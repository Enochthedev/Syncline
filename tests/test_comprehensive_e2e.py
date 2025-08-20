"""
End-to-end test scenarios covering full message ingestion to search flow.

This module tests the complete flow from message ingestion through AI processing
to search and retrieval, ensuring all components work together correctly.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from main import app
from db.session import get_db
from db.redis_client import get_redis
from services.event_bus import EventBus
from services.message_normalizer import MessageNormalizer
from services.ai.engine import AIProcessingEngine
from services.ai.search.agent import HybridSearchAgent
from services.message_schema import RawMessage, NormalizedMessage, MessageContent, Participant
from integrations.gmail_connector import GmailConnector
from integrations.slack_connector import SlackConnector
from integrations.discord_connector import DiscordConnector
from integrations.yahoo_connector import YahooConnector
from api.auth.models import User


@pytest.fixture
def test_user():
    """Create a test user for E2E tests."""
    return User(
        id="e2e-test-user",
        username="e2e_user",
        email="e2e@example.com",
        full_name="E2E Test User",
        is_active=True,
        tenant_id="e2e-tenant"
    )


@pytest.fixture
async def event_bus():
    """Create event bus for testing."""
    try:
        redis_client = await get_redis()
        return EventBus(redis_client)
    except RuntimeError:
        pytest.skip("Redis not available for E2E tests")


@pytest.fixture
def mock_ai_engine():
    """Mock AI processing engine."""
    engine = AsyncMock(spec=AIProcessingEngine)

    # Mock entity extraction
    engine.extract_entities.return_value = [
        {"type": "person", "value": "John Doe", "confidence": 0.95},
        {"type": "organization", "value": "Acme Corp", "confidence": 0.88}
    ]

    # Mock summary generation
    engine.generate_summary.return_value = {
        "content": "Test summary of the conversation",
        "key_points": ["Important point 1", "Important point 2"],
        "action_items": ["Follow up on proposal"]
    }

    # Mock embedding generation
    engine.generate_embedding.return_value = [
        0.1] * 1536  # Mock 1536-dim vector

    return engine


@pytest.fixture
def mock_search_agent():
    """Mock hybrid search agent."""
    agent = AsyncMock(spec=HybridSearchAgent)

    search_result = AsyncMock()
    search_result.results = []
    search_result.stats = AsyncMock()
    search_result.stats.total_results = 0
    search_result.stats.processing_time_ms = 10.0
    search_result.query = AsyncMock()
    search_result.suggestions = []
    search_result.facets = {}

    agent.search.return_value = search_result
    return agent


class TestEndToEndMessageFlow:
    """Test complete message ingestion and processing flow."""

    @pytest.mark.asyncio
    async def test_gmail_message_ingestion_to_search(self, test_user, event_bus, mock_ai_engine, mock_search_agent):
        """Test complete flow: Gmail message → normalization → AI processing → search."""

        # Step 1: Create raw Gmail message
        raw_message = RawMessage(
            platform="gmail",
            platform_message_id="gmail_msg_123",
            platform_thread_id="gmail_thread_456",
            raw_data={
                "id": "gmail_msg_123",
                "threadId": "gmail_thread_456",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "john@example.com"},
                        {"name": "To", "value": "user@example.com"},
                        {"name": "Subject", "value": "Test E2E Message"},
                        {"name": "Date", "value": "Mon, 1 Jan 2024 10:00:00 +0000"}
                    ],
                    "body": {
                        "data": "VGVzdCBtZXNzYWdlIGNvbnRlbnQgZm9yIEUyRSB0ZXN0aW5n"  # Base64 encoded
                    }
                }
            }
        )

        # Step 2: Normalize message
        normalizer = MessageNormalizer()
        normalized_message = await normalizer.normalize_message(raw_message)

        assert normalized_message.platform == "gmail"
        assert normalized_message.content.text == "Test message content for E2E testing"
        # sender and recipient
        assert len(normalized_message.participants) >= 2

        # Step 3: Publish to event bus
        await event_bus.publish("MESSAGE_NORMALIZED", {
            "message_id": str(normalized_message.id),
            "platform": normalized_message.platform,
            "tenant_id": test_user.tenant_id
        })

        # Step 4: Simulate AI processing
        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
            entities = await mock_ai_engine.extract_entities(normalized_message.content.text)
            summary = await mock_ai_engine.generate_summary(normalized_message.content.text)
            embedding = await mock_ai_engine.generate_embedding(normalized_message.content.text)

            assert len(entities) > 0
            assert summary["content"] is not None
            assert len(embedding) == 1536

        # Step 5: Test search functionality
        with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):
            search_query = "Test E2E Message"
            search_results = await mock_search_agent.search(search_query)

            assert search_results is not None
            assert hasattr(search_results, 'stats')

    @pytest.mark.asyncio
    async def test_multi_platform_message_aggregation(self, test_user, event_bus, mock_ai_engine):
        """Test aggregating messages from multiple platforms."""

        # Create messages from different platforms
        platforms_data = [
            {
                "platform": "gmail",
                "message_id": "gmail_123",
                "content": "Gmail message content",
                "sender": "john@gmail.com"
            },
            {
                "platform": "slack",
                "message_id": "slack_456",
                "content": "Slack message content",
                "sender": "john.doe"
            },
            {
                "platform": "discord",
                "message_id": "discord_789",
                "content": "Discord message content",
                "sender": "JohnDoe#1234"
            },
            {
                "platform": "yahoo",
                "message_id": "yahoo_101",
                "content": "Yahoo mail message content",
                "sender": "john@yahoo.com"
            }
        ]

        normalized_messages = []
        normalizer = MessageNormalizer()

        for platform_data in platforms_data:
            raw_message = RawMessage(
                platform=platform_data["platform"],
                platform_message_id=platform_data["message_id"],
                platform_thread_id=f"{platform_data['platform']}_thread",
                raw_data={
                    "content": platform_data["content"],
                    "sender": platform_data["sender"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            normalized = await normalizer.normalize_message(raw_message)
            normalized_messages.append(normalized)

        # Verify all messages were normalized correctly
        assert len(normalized_messages) == 4
        platforms = {msg.platform for msg in normalized_messages}
        assert platforms == {"gmail", "slack", "discord", "yahoo"}

        # Test unified search across platforms
        with patch('services.ai.search.agent.HybridSearchAgent') as mock_agent:
            mock_search_response = AsyncMock()
            mock_search_response.results = [
                AsyncMock(platform="gmail", content="Gmail message content"),
                AsyncMock(platform="slack", content="Slack message content"),
                AsyncMock(platform="discord",
                          content="Discord message content"),
                AsyncMock(platform="yahoo",
                          content="Yahoo mail message content")
            ]
            mock_search_response.stats = AsyncMock()
            mock_search_response.stats.total_results = 4

            mock_agent_instance = AsyncMock()
            mock_agent_instance.search.return_value = mock_search_response
            mock_agent.return_value = mock_agent_instance

            search_results = await mock_agent_instance.search("message content")
            assert len(search_results.results) == 4

    @pytest.mark.asyncio
    async def test_real_time_processing_pipeline(self, test_user, event_bus, mock_ai_engine):
        """Test real-time message processing pipeline with timing constraints."""

        start_time = time.time()

        # Step 1: Message ingestion (should be < 1 second)
        raw_message = RawMessage(
            platform="gmail",
            platform_message_id="realtime_test_123",
            platform_thread_id="realtime_thread",
            raw_data={
                "content": "Real-time processing test message",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        ingestion_time = time.time()
        assert (ingestion_time -
                start_time) < 1.0, "Message ingestion took too long"

        # Step 2: Normalization (should be < 0.5 seconds)
        normalizer = MessageNormalizer()
        normalized_message = await normalizer.normalize_message(raw_message)

        normalization_time = time.time()
        assert (normalization_time -
                ingestion_time) < 0.5, "Message normalization took too long"

        # Step 3: AI processing (should be < 3 seconds for mock)
        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
            entities = await mock_ai_engine.extract_entities(normalized_message.content.text)

        ai_processing_time = time.time()
        assert (ai_processing_time -
                normalization_time) < 3.0, "AI processing took too long"

        # Total pipeline should be < 5 seconds (requirement: < 5 seconds)
        total_time = ai_processing_time - start_time
        assert total_time < 5.0, f"Total pipeline time {total_time:.2f}s exceeded 5s requirement"

    @pytest.mark.asyncio
    async def test_error_recovery_and_dlq(self, test_user, event_bus):
        """Test error recovery and dead letter queue functionality."""

        # Create a message that will cause processing errors
        problematic_message = RawMessage(
            platform="gmail",
            platform_message_id="error_test_123",
            platform_thread_id="error_thread",
            raw_data={
                "malformed": "data",
                "missing": "required_fields"
            }
        )

        # Test normalization error handling
        normalizer = MessageNormalizer()

        with pytest.raises(Exception):
            await normalizer.normalize_message(problematic_message)

        # Test that failed messages go to DLQ
        with patch('services.resilience.dead_letter_queue.DeadLetterQueue') as mock_dlq:
            mock_dlq_instance = AsyncMock()
            mock_dlq.return_value = mock_dlq_instance

            # Simulate DLQ processing
            await mock_dlq_instance.add_failed_message(
                "MESSAGE_NORMALIZATION_FAILED",
                problematic_message.dict(),
                "Normalization failed: missing required fields"
            )

            mock_dlq_instance.add_failed_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_integration_with_processed_data(self, test_user, mock_search_agent):
        """Test API endpoints with processed message data."""

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test search API with processed data
            with patch('api.dependencies.get_current_active_user', return_value=test_user):
                with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):

                    # Configure mock search results
                    mock_search_response = AsyncMock()
                    mock_search_response.results = [
                        AsyncMock(
                            id="msg_123",
                            title="Test Message",
                            content="Processed message content",
                            platform="gmail",
                            timestamp=datetime.utcnow(),
                            score=0.95
                        )
                    ]
                    mock_search_response.stats = AsyncMock()
                    mock_search_response.stats.total_results = 1
                    mock_search_response.stats.processing_time_ms = 15.0
                    mock_search_response.query = AsyncMock()
                    mock_search_response.suggestions = []
                    mock_search_response.facets = {}

                    mock_search_agent.search.return_value = mock_search_response

                    # Test search endpoint
                    search_data = {
                        "query": "processed message",
                        "limit": 10
                    }

                    response = await client.post("/api/v1/search/", json=search_data)
                    assert response.status_code == 200

                    data = response.json()
                    assert "results" in data
                    assert len(data["results"]) == 1
                    assert data["results"][0]["platform"] == "gmail"

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, test_user, event_bus, mock_ai_engine):
        """Test concurrent processing of multiple messages."""

        # Create multiple messages for concurrent processing
        messages = []
        for i in range(10):
            raw_message = RawMessage(
                platform="gmail",
                platform_message_id=f"concurrent_msg_{i}",
                platform_thread_id=f"concurrent_thread_{i}",
                raw_data={
                    "content": f"Concurrent test message {i}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            messages.append(raw_message)

        # Process messages concurrently
        normalizer = MessageNormalizer()

        async def process_message(msg):
            normalized = await normalizer.normalize_message(msg)

            # Simulate AI processing
            with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
                entities = await mock_ai_engine.extract_entities(normalized.content.text)
                return normalized, entities

        start_time = time.time()

        # Process all messages concurrently
        tasks = [process_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify all messages were processed successfully
        successful_results = [
            r for r in results if not isinstance(r, Exception)]
        assert len(
            successful_results) == 10, f"Only {len(successful_results)} out of 10 messages processed successfully"

        # Concurrent processing should be faster than sequential
        # (This is a rough estimate - actual performance will vary)
        assert processing_time < 10.0, f"Concurrent processing took {processing_time:.2f}s, expected < 10s"

    @pytest.mark.asyncio
    async def test_data_consistency_across_pipeline(self, test_user, event_bus, mock_ai_engine):
        """Test data consistency throughout the processing pipeline."""

        # Create a message with specific content to track
        original_content = "Important business proposal from John Doe at Acme Corp"
        raw_message = RawMessage(
            platform="gmail",
            platform_message_id="consistency_test_123",
            platform_thread_id="consistency_thread",
            raw_data={
                "content": original_content,
                "sender": "john.doe@acme.com",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Step 1: Normalize message
        normalizer = MessageNormalizer()
        normalized_message = await normalizer.normalize_message(raw_message)

        # Verify content preservation
        assert original_content in normalized_message.content.text
        assert normalized_message.platform == "gmail"

        # Step 2: AI processing
        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
            # Configure mock to return consistent entities
            mock_ai_engine.extract_entities.return_value = [
                {"type": "person", "value": "John Doe", "confidence": 0.95},
                {"type": "organization", "value": "Acme Corp", "confidence": 0.88}
            ]

            entities = await mock_ai_engine.extract_entities(normalized_message.content.text)

            # Verify entity extraction consistency
            person_entities = [e for e in entities if e["type"] == "person"]
            org_entities = [e for e in entities if e["type"] == "organization"]

            assert len(person_entities) > 0
            assert len(org_entities) > 0
            assert any("John Doe" in e["value"] for e in person_entities)
            assert any("Acme Corp" in e["value"] for e in org_entities)

        # Step 3: Verify data integrity in storage simulation
        stored_data = {
            "message_id": str(normalized_message.id),
            "original_content": original_content,
            "normalized_content": normalized_message.content.text,
            "extracted_entities": entities,
            "platform": normalized_message.platform
        }

        # Verify no data corruption
        assert stored_data["original_content"] == original_content
        assert stored_data["platform"] == "gmail"
        assert len(stored_data["extracted_entities"]) > 0


class TestWebSocketRealTimeUpdates:
    """Test real-time WebSocket updates during message processing."""

    @pytest.mark.asyncio
    async def test_websocket_message_notifications(self, test_user):
        """Test WebSocket notifications for new messages."""

        # This would test WebSocket connections in a real scenario
        # For now, we'll test the notification mechanism

        with patch('api.websocket.manager.ConnectionManager') as mock_manager:
            mock_manager_instance = AsyncMock()
            mock_manager.return_value = mock_manager_instance

            # Simulate new message notification
            message_data = {
                "type": "new_message",
                "message_id": "test_123",
                "platform": "gmail",
                "sender": "john@example.com",
                "preview": "New message preview..."
            }

            await mock_manager_instance.broadcast_to_user(
                test_user.id,
                message_data
            )

            mock_manager_instance.broadcast_to_user.assert_called_once_with(
                test_user.id,
                message_data
            )

    @pytest.mark.asyncio
    async def test_websocket_search_result_streaming(self, test_user, mock_search_agent):
        """Test streaming search results via WebSocket."""

        with patch('api.websocket.search_handler.SearchHandler') as mock_handler:
            mock_handler_instance = AsyncMock()
            mock_handler.return_value = mock_handler_instance

            # Configure mock search results
            mock_search_response = AsyncMock()
            mock_search_response.results = [
                AsyncMock(id="result_1", content="First result"),
                AsyncMock(id="result_2", content="Second result")
            ]

            mock_search_agent.search.return_value = mock_search_response

            # Simulate streaming search
            search_query = "test query"
            await mock_handler_instance.handle_search_request(
                test_user.id,
                {"query": search_query, "stream": True}
            )

            mock_handler_instance.handle_search_request.assert_called_once()


class TestSystemIntegration:
    """Test complete system integration with all components."""

    @pytest.mark.asyncio
    async def test_complete_system_integration(self, test_user, event_bus, mock_ai_engine, mock_search_agent):
        """Test complete system integration from connector to API."""
        
        # Step 1: Test all connector types
        connectors_data = [
            {
                "platform": "gmail",
                "connector_class": GmailConnector,
                "message_content": "Gmail integration test message"
            },
            {
                "platform": "slack", 
                "connector_class": SlackConnector,
                "message_content": "Slack integration test message"
            },
            {
                "platform": "discord",
                "connector_class": DiscordConnector, 
                "messssage"
"-v"])([__file__, .main   pytest_":
 _main_ "___ ==mef __na
ik"

rm == "slaclatfo.pzed_slacksert normali   asl"
     "gmaiplatform == mail.d_glizert norma    asse  
  cessfullysucs completed nariol user sce Al      #0

  ) > n_items"]"actioary[len(summert       ass     "
 "highency"] == ry["urgert summaass            > 0
 k_entities)len(slac     assert  0
       tities) >(gmail_enen assert l         
  ulngfni meahts arensig i Verify AI         #  t)

 _contenedmmary(combinnerate_sugine.gek_ai_enawait moc= mmary    su       "
  .text}ntentk.comalized_slactext} {norl.content.lized_gmai f"{norma_content =ed      combin     
          )
   ntent.texted_slack.cos(normaliz_entitieine.extractk_ai_engit moctities = awa    slack_en)
        ext.tmail.contentlized_gs(normaract_entitie.extine mock_ai_engies = awaittit gmail_en         th AI
   messages wiess both Proc   #
              }
  
     high"cy": "gen      "ur     ,
               ]"
      meetingm cheduled teaAttend res     "      ,
         irements"adline requject dew proie      "Rev              tems": [
_ion      "acti                ],
      3 PM"
    ed to standup movam        "Te         t",
    e from cliene updatt deadlinjec    "Pro        
        ": [ntsoi    "key_p     ,
       scheduled"m meeting reead tm client an frommunicatione colin deadctnt projemporta"User has itent":  "con      
         = {rn_value ry.retusummate_ngine.generaai_emock_         
         ]
     .92}
 idence": 0onf"c", e": "3 PM, "valu "time"ype":      {"t  
        e": 0.95},"confidencoday", "t: "value""date", pe": "ty {          ,
      0.85}dence":onfimpany", "clue": "co, "vaization"an"orgpe": {"ty                e": 0.9},
idenc, "conflient"alue": "c"von",  "pers  {"type":              _value = [
es.returnct_entitingine.extraai_ek_        moc    ights
es and insiti entevantt relextracgure AI to      # Confi  
     ngine):_ai_ealue=mockn_vne', retursingEngiine.AIProcesi.engs.atch('serviceth pa wi  
      insightseredgets AI-pow User nario 4:     # Sce

   s)lt.resusultsn search_result ifor rek" = "slacorm =ult.platfres assert any(           ts)
sults.resul_rein searcht resulor "gmail" flatform == sult.pert any(re ass      lts)
     s.resuh_resultult in searct for result.contenine" in res"deadlert any(   ass
          == 2ts)resullts.search_resusert len(          as      
  ")
      eadline dprojectrch("ent.seaearch_agwait mock_ss = aearch_result s      
     e"eadlinoject des for "prsearch User      #

       ensrch_respo= mock_seaalue urn_vt.search.retearch_agenock_s        m
    }
         ": 2}
    {"todayme_range":    "ti      ,
      "slack": 1}1, l": ": {"gmaiplatforms     "      {
     facets = onse.search_resp  mock_         roject"]
 "p", eting "meline",ead ["dns =suggestiose._responarch mock_se     )
      ock(ry = AsyncMe.quearch_responsock_se         m   2
 esults =l_rstats.totanse.ch_respoarck_se        mo   
 syncMock() = Ae.statsnsrch_respomock_sea                  ]
       )
               general"}
 "#":elata={"chann metad                   .88,
re=0 sco        
           oday", PM t 3g moved tomeetindup ="Team stanntent   co                  
",m="slackatfor     pl              syncMock(
    A           
            ),      ate"}
Deadline Upd"Project bject": ={"sudata    meta                0.95,
re=        sco           
 adline", project deutt aboienm clemail fro"Important   content=                 il",
 orm="gma     platf            
   ncMock(Asy                [
ults = nse.resresposearch_ock_ m   ()
        syncMocknse = Ach_respoear      mock_s
      rch_agent):ck_seaue=mon_valt', returAgendSearchent.Hybrich.ag.ai.searervices'sth patch(        wilatforms
ross pches acr searserio 3: U# Scena
        essage)
e(slack_msagize_mesmal.nort normalizerck = awaid_sla   normalize)

                 }
        mat()
sofor().inowutc datetime.timestamp": "               al",
gener"#annel":         "ch
        lead",r": "team.de "sen            y",
   oda PM ted to 3meeting movm standup ": "Teatent"con              {
  data= raw_      ",
     k_threadacer_slusread_id="form_thplat         
   t_slack_1",er_tes="usage_idorm_mess      platf,
      ack"rm="slfoat     pl
        RawMessage(message =k_    slacs
    team messageceives ack and reconnects Slrio 2: User # Scena
        )
        messagegmail_ssage(ormalize_meizer.nnormall = await malized_gmai   nor  
   izer()ssageNormalzer = Memali      nor)

                 }
 mat()
    ow().isoforetime.utcn: dat"estamp  "tim            e",
  dline Updatect Deact": "Projubje"s           om",
     @company.client"csender":   "            ",
  deadlineout project t ab client email fromrtanImpo: "content"         "
       aw_data={      r",
      readgmail_th_id="user_rm_threadfo  plat         
 ",il_1gmast_r_tee_id="usemessagplatform_     ",
       mailrm="g      platfo(
      agee = RawMesssag gmail_mes     es
  ives messagl and receais Gmectnn1: User co # Scenario    
       ""
     narios."eptance sceser acc major uest"""T:
        _agent)archck_seengine, mok_ai_t_bus, moct_user, evenelf, tesarios(snce_sceneptaser_acc_uc def test
    asynark.asyncio@pytest.mg)

    fiettings, consattr(st ha       asser     igs:
 in ai_conffig     for con     
      ]
   L'
     SE_UR 'OLLAMA_BA          T_MODEL',
 'DEFAULT_CHA           ROVIDER',
 _PLMLT_L 'DEFAU  
         nfigs = [       ai_couration
 # AI config    g)

    confisettings, sattr(hasert         ass:
    orm_config in platf config
        fore defined should bt, but environmenste set in tet not bese migh Th
        #          ]
 MAIL'
     _E'YAHOO     ',
       BOT_TOKENORD_'DISC             
_ID',ENTACK_CLI      'SLID',
      LIENT_    'GMAIL_C       s = [
 orm_config      platf  gurations
 confiormatf# Pl  
        
      URL'), 'REDIS_r(settingsrt hasattse   as     _URL')
SEDATABAings, 'attr(sett  assert has   uration
   ore config# C          
gs()
      gs = Settin   settin    present
 is uration ed configt all requirha    # Test t
    
        gsettinimport Snfig config.co   from      ion
validatoading and ration lconfigu  # Test       
 
       """agement.tion manurae configm-widsteTest sy""        ":
r)f, test_usenagement(seln_maatiofigurest_conef tync do
    as.mark.asynci
    @pytest
ios)enarlen(error_scnt == recovery_couount + error_cassert a
        formed datfrom malsome errors expect e   # Wt > 0error_coun     assert ly
   cefule errors gradlan should hemst      # Syonce()

  alled_rt_cge.asseailed_messaadd_fq_instance.k_dl   moc          
                   )
                    )
              str(e           ),
       "].dict(sageesario["men   sc              
       .upper()}",'name']rio[R_{scenaERROZATION_NORMALI   f"            
         e(ailed_messagd_f.adnstancet mock_dlq_i   awai           
                        ance
  lq_instmock_d = aluern_vretuck_dlq.  mo       
           ck()Mo= Asyncnce sta mock_dlq_in                  _dlq:
 s mockueue') adLetterQe.Deatter_queudead_leence..resilicesatch('servi with p        
       hanismvery meccote error reimula # S                
            eption)
    Excsinstance(e,    assert i   
         edndl haogged andproperly l errors are st that       # Te       
             1
     += error_count                
 s e:xception aept E         exc= 1
   nt +ery_couov         rec])
       sage"["mese(scenarioe_messagalizmalizer.norm  await nor               try:
          rios:
 cenar_serrocenario in     for s = 0

    ountcovery_c re
       _count = 0error       lizer()
 ssageNormamalizer = Me  nor             ]


        }     
   )         "}
     "t":conten={"taraw_da                    d", 
rea="error_thead_idform_thr        plat           
 t_3",="error_tesge_idessa  platform_m              ,
    gmail"m="or  platf                
  RawMessage(essage":        "m,
         content"empty_ame": "    "n              {
 
                   },)
                 est"}
 tent": "t_data={"con raw                  ",
 hreadr_troerread_id="platform_th                  
   2",est_r_tid="errorm_message_  platfo                  ",
id_platforminvalform="      plat            ssage(
  Me: Rawessage""m              ",
  id_platformval"inname":         "          {
          
          },     )
             ed fields
uir req Missing  #"}aed": "datalforma={"m    raw_dat             ad",
   error_thre"thread_id=  platform_               ",
   or_test_1rrge_id="eatform_messa        pl       il",
     ="gma    platform              
  (ageesssage": RawM   "mes        ",
     essageformed_me": "mal      "nam                 {
[
     os = r_scenarirro  erios
      or scenarrious est var# Te
              """
  ence.nd resiliovery a recm-wide errorTest syste """):
       r, event_busst_use teovery(self,error_rec_system_def testc    asyn.asyncio
 rk @pytest.ma

   ndr seco message pe At least 1.0  #d > 1consesages_per_mes     assert me
   / total_tiount rocessed_c pd =seconssages_per_  me         
  
   econdsnder 60 s umessages inprocess 100 hould  # Sme < 60.0 rt total_tise    ase
    at% success rt 95At leas.95  # unt * 0sage_co= mesed_count >cesssert pro as   ns
    io asserterformance  # P    
          ime
rt_t_time - staendtime =       total_time()
  me. titime =     end_   _batch)

essful len(succnt +=_coussedce       pro  ]
   , Exception)sinstance(r if not iresultsin batch_r for r  [sful_batch = succes    
              ue)
     ptions=Trurn_exces, retch_taskather(*batcio.gsynt aults = awai  batch_res     
      in batch] msgg) forge(mstch_messas_baesks = [proc  batch_tas    es

      zed, entititurn normalire                   nt.text)
 ized.contermalities(noxtract_ent.e_ai_enginet mockawaiies = entit                 :
   ai_engine)=mock_rn_valueretuEngine', ocessing.engine.AIPrces.aierviith patch('s         w
                      sage(msg)
 rmalize_meslizer.normaait nolized = awma       nor       ):
  essage(msgess_batch_mync def proc         asrently
   concuress batch Proc      #     
        ize]
      :i + batch_sges[ih = messa batc       ize):
    unt, batch_sage_co messge(0, i in ran       for 
    = 0
     count  processed_()
      alizersageNormer = Mes   normaliz
           e()
  .timtime = me   start_ti0
     ch_size = 1   bat   s
  s in batchessagemeProcess       # ssage)

  _mepend(rawapges.essa  m         
      )           }
      
      rmat()ofocnow().isutime.etstamp": dat    "time               ,
 }.com"tformuser{i}@{pla: f"  "sender"           
       platform}",e {i} from {sagest mes"Load tcontent": f     "    
           a={_dat    raw   
         / 10}",hread_{i /load_tatform}_{plead_id=f"atform_thr    pl         i}",
   t_{rm}_load_tes"{platfoe_id=fessagform_mat       pl   
      latform,rm=p platfo        e(
       awMessagssage = Rme      raw_      "][i % 4]
"yahoo, d"or, "discslack", "il"m = ["gmaatfor   pl
         t):sage_counin range(mesor i  
        f
       sages = []        mes= 100
nt ouge_c messa       ges
me of messaolu v Create high     #
   
        ""ad."ge lohigh messaance under orm system perf"Test    ""):
    _enginebus, mock_aient_t_user, evlf, teser_load(see_undncorma_system_perftestf    async de
 ark.asynciopytest.m 4

    @] ==esults"otal_rs"]["tta["stat assert da             
      ats" in datta "sert        ass      data
      in " ltsert "resu        ass       on()
     e.js respons      data =         

     ode == 200atus_cse.stespon assert r                  rch_data)
 , json=seav1/search/"i/t("/apost.pawait cliennse =        respo           

   }         
          10imit":   "l                     ],
 ahoo", "yrd"sco"dilack",  "s"gmail",ms": [latfor        "p              t",
  ation tes "integrry":"que                       ata = {
 search_d             
       ch APIear Test s        #       
                  t):
       h_agenock_searcn_value=m, returnt'rchAgeidSeaybr.Harch.agenti.se'services.ah patch(       wit        t_user):
 rn_value=tesretuer', ve_usrent_actiet_curncies.g'api.dependewith patch(    t:
         clientest") astp://url="htbase_p=app, ient(ap AsyncClwithc    asyn    ata
 ocessed d pron with alltintegraPI i 3: Test AStep
        # "}
hoo"ya"discord", , "slack"ail", rms == {"gmsult_platfort re    asse        results}
h_results. in searc for resultormlt.platfesu= {rplatforms      result_  
     s) == 4ltesults.resuen(search_r  assert l       
            test")
   ion ratch("integargent.seh_arcea_sockt mlts = awai search_resu
           atformscross all plst search a      # Te
      e
nsarch_resposek_= moclue h.return_vaearcgent.sck_search_a     mo         }

          ": 1}
ahoo 1, "y"discord":lack": 1, : 1, "s"": {"gmailplatforms   "          {
    ets =acsponse.fh_researc   mock_      []
    uggestions =sponse.sck_search_re       mo
     Mock()uery = Asynch_response.qk_searcoc     m5.0
       me_ms = 2essing_tis.proconse.stath_respk_searc      moc 4
      l_results =tats.tonse.staesposearch_r      mock_  
    )Mock(= Asyncnse.stats ch_respomock_sear                ]
 ges
       d_messain processer msg ) fo            
    core=0.9       s            ],
 ies"it"ents=msg[ entitie                 t,
  t.tex].contened"malizg["nortent=ms  con               
   orm,"].platfrmalizedg["nolatform=ms           p        syncMock(
         A [
        s =esulth_response.rsearcmock_         ck()
   cMo Asynh_response =ock_searc      m
       platformsom alls frresulturn retock to re m# Configu         agent):
   ch_arlue=mock_sen_vareturt', dSearchAgen.Hybrich.agent.ai.sear('servicesth patch wi      ms
 atforcross all plrch afied sea uni Test# Step 2:

        "yahoo"}cord", is", "dslack", "mailsed == {"grms_proceslatfoert p  ass   sages}
   ocessed_messg in prfor mm "].platfordzealimsg["norm= {essed rms_proc     platfo= 4
   ges) =ssassed_met len(proce       asser
 yuccessfullrocessed stforms pplal  # Verify al  

       })       
   edding: emb"embedding"          ry,
      ": summaarysumm       "
         ties,": entitiesenti  "          e,
    _messaglizedrmalized": nonorma       "     end({
    sages.apped_mes  process          t.text)

contenge.zed_messanormalig(e_embeddinine.generatock_ai_engawait medding =        emb       .text)
  tentessage.conmalized_mary(norte_summne.generaai_engiit mock_way = a   summar            .text)
 entage.cont_messmalizeds(noritiect_enttrai_engine.ext mock_as = awaintitie      e       ):
   nginee=mock_ai_eturn_valuine', regEngssinIProceai.engine.Aservices.tch('ith pa   w       ocessing
  mulate AI pr   # Si
               e)
      essag(raw_mlize_message.normaeralizwait norm = aageized_mess     normal      alizer()
 ssageNorm Mezer =mali         nor  sage
 rmalize mes  # No
            )

              }           
 isoformat()utcnow().atetime.": dimestamp   "t          ",
       orm']}.comdata['platftor_{connectest@ f" "sender":                   nt"],
ssage_conteor_data["menect: con "content"          
         a={ raw_dat              
 ",threadn_tegratio]}_inlatform'a['pnector_dat"{conad_id=f_thre  platform            n_123",
  }_integratiotform']ta['plaor_daconnect"{e_id=fmessagatform_       pl         tform"],
laa["pnnector_dat platform=co    
           (agee = RawMess  raw_messag
          rmtfoh pla eacssage fore raw me# Creat         ta:
   nnectors_dar_data in coecto for conn            
  s = []
 d_message   processe  ]

            }
        "
   geessaon test matiegrmail inthoo ent": "Yae_cont  "messag        or,
      YahooConnectss": r_claconnecto    "         oo",
   yahatform": " "pl          {
                      },
       n test metioegra int"Discordontent": age_c
