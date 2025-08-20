"""
Performance and load tests for high-volume message processing and concurrent users.

This module tests system performance under various load conditions.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch
import random
import string

from services.message_normalizer import MessageNormalizer
from services.ai.engine import AIProcessingEngine
from services.ai.search.agent import HybridSearchAgent
from services.message_schema import RawMessage
from api.auth.models import User

# Performance test configuration
PERFORMANCE_CONFIG = {
    "high_volume_message_count": 1000,
    "concurrent_users": 50,
    "max_processing_time": 5.0,
    "max_search_time": 1.0,
    "batch_size": 100,
}


@pytest.fixture
def performance_test_users():
    """Create multiple test users for concurrent testing."""
    users = []
    for i in range(20):
        user = User(
            id=f"perf-user-{i}",
            username=f"perfuser{i}",
            email=f"perfuser{i}@example.com",
            full_name=f"Performance User {i}",
            is_active=True,
            tenant_id=f"perf-tenant-{i % 5}"
        )
        users.append(user)
    return users


@pytest.fixture
def mock_ai_engine_fast():
    """Fast mock AI engine for performance testing."""
    engine = AsyncMock(spec=AIProcessingEngine)
    
    # Fast mock responses
    engine.extract_entities.return_value = [
        {"type": "person", "value": "Test Person", "confidence": 0.9}
    ]
    engine.generate_summary.return_value = {
        "content": "Quick summary",
        "key_points": ["Point 1"],
        "action_items": []
    }
    engine.generate_embedding.return_value = [0.1] * 1536
    
    # Add small delay to simulate processing
    async def mock_with_delay(*args, **kwargs):
        await asyncio.sleep(0.01)  # 10ms delay
        return engine.extract_entities.return_value
    
    engine.extract_entities.side_effect = mock_with_delay
    
    return engine


def generate_random_message(platform: str = "gmail", message_id: str = None) -> RawMessage:
    """Generate a random message for testing."""
    if message_id is None:
        message_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    content_templates = [
        "Hello, this is a test message about {topic}.",
        "Meeting scheduled for {date} regarding {project}.",
        "Follow up on the {project} project.",
        "Important update regarding {topic}.",
        "Thank you for your email about {topic}."
    ]
    
    topics = ["project alpha", "quarterly review", "budget planning", "team meeting"]
    dates = ["tomorrow", "next week", "Friday", "end of month"]
    
    content = random.choice(content_templates).format(
        topic=random.choice(topics),
        date=random.choice(dates),
        project="test project"
    )
    
    return RawMessage(
        platform=platform,
        platform_message_id=f"{platform}_{message_id}",
        platform_thread_id=f"{platform}_thread_{message_id[:5]}",
        raw_data={
            "content": content,
            "sender": f"user{random.randint(1, 100)}@example.com",
            "timestamp": datetime.utcnow().isoformat(),
            "subject": f"Test Subject {message_id[:5]}"
        }
    )


class TestHighVolumeMessageProcessing:
    """Test high-volume message processing performance."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_bulk_message_normalization(self):
        """Test normalizing large batches of messages."""
        
        message_count = 100  # Reduced for testing
        messages = [generate_random_message() for _ in range(message_count)]
        
        normalizer = MessageNormalizer()
        
        start_time = time.time()
        
        # Process messages in batches
        batch_size = 20
        normalized_messages = []
        
        for i in range(0, message_count, batch_size):
            batch = messages[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [normalizer.normalize_message(msg) for msg in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            successful = [r for r in batch_results if not isinstance(r, Exception)]
            normalized_messages.extend(successful)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        success_rate = len(normalized_messages) / message_count
        avg_processing_time = total_time / message_count
        
        assert success_rate > 0.90, f"Success rate {success_rate:.2%} below 90%"
        assert avg_processing_time < 0.1, f"Average processing time {avg_processing_time:.3f}s exceeds 0.1s"
        
        print(f"Processed {len(normalized_messages)} messages in {total_time:.2f}s")
        print(f"Average time per message: {avg_processing_time:.3f}s")
        print(f"Success rate: {success_rate:.2%}")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_ai_processing(self, mock_ai_engine_fast):
        """Test concurrent AI processing of messages."""
        
        message_count = 50
        messages = [generate_random_message() for _ in range(message_count)]
        
        normalizer = MessageNormalizer()
        
        # Normalize messages first
        normalized_messages = []
        for msg in messages:
            try:
                normalized = await normalizer.normalize_message(msg)
                normalized_messages.append(normalized)
            except Exception:
                continue
        
        # Test AI processing
        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine_fast):
            
            async def process_with_ai(message):
                start_time = time.time()
                
                entities = await mock_ai_engine_fast.extract_entities(message.content.text)
                
                processing_time = time.time() - start_time
                return {
                    "message_id": str(message.id),
                    "entities": entities,
                    "processing_time": processing_time
                }
            
            start_time = time.time()
            
            # Process messages concurrently
            tasks = [process_with_ai(msg) for msg in normalized_messages]
            results = await asyncio.gather(*tasks, return_exceptions=True)
       e"])nc "performa",, "-m-v"file__, "[__ytest.main(:
    pn__""__mai_ ==  __name_


ifs")action:.3f}tr_time_per_extion: {avgacime per extrage t"Averrint(f         pf}s")
   _time:.2als in {totes)} message(all_entitim {lenies fro entitractedint(f"Ext      pr
                o slow"
  s toction:.3f}me_per_extra {avg_tin timeextractioAverage .2, f"ion < 0actper_extrt avg_time_sser    a"
        %elow 90rate:.2%} bsuccess_ {ess rateion succctity extra"Ent0, f> 0.9ccess_rate  sussert a   s
        assertionmance rforPe          #            
sages)
   ized_mesen(normale / ltal_timtion = toacextrr_avg_time_pe        ges)
    alized_messarmlen(noes) / l_entitien(al = less_rate      succ        
    
      _timeime - startime = end_t  total_t          me.time()
tind_time =          e 
           )
   essful_entititend(success.extie_enti      all          tion)]
e, Excepstance( if not isinitiesnth_ebatce for e in ies = [itssful_ent     succe       )
    ns=Trueceptiorn_exasks, retur(*tncio.gatheit asywa a =iestch_entit       ba    
                      ]
           batch
    r msg in    fo               ext)
  content.t(msg._entitiesract_fast.extck_ai_engine    mo             = [
           tasks 
                       ze]
 atch_sis[i:i + b_messagemalized= nor      batch         e):
  , batch_sizges)ssalized_meorma len(n0,n range(or i i       f
          ]
       ities = [entl_          al
  h_size = 10atc    b
        es in batchentities# Extract      
             ()
      = time.time_time    start     
    _fast):nengii_evalue=mock_an_urngine', retcessingE.AIProinei.eng('services.a with patch  
             inue
        cont        Exception:
ept xc           ezed)
 aliend(normappmessages.d_lize    norma           e(msg)
 e_messag.normalizrmalizert noed = awai  normaliz              try:
       ages:
      msg in mess      fores = []
  messagzed_  normali      ssages
alize me Norm
        #
        ()zergeNormalisazer = Mesormali        n(50)]
range_ in for () ssagerandom_mete_= [genera  messages             
  e."""
formancaction pertity extr en batch""Test      "  e_fast):
_engin mock_ailf,ion(seity_extracth_entest_batcsync def t  ae
  k.performanctest.mar   @py.asyncio
 markpytest. @}s")

   ing:.3fper_embeddme_ng: {avg_tiper embeddime rage tivent(f"A       pri
     )ime:.2f}s"tal_tgs in {to embeddins)}l_embeddingccessfulen(suted {Generaf"rint(           p   
 
          slow"}s toobedding:.3fper_emvg_time_e {aing timmbedd"Average e1, fing < 0.mbeddr_eime_pert avg_t asse     
      elow 95%"rate:.2%} buccess_ate {scess rdding suc"Embete > 0.95, fs_raucces    assert s       
  assertionserformance# P     
                  en(texts)
 time / ltal_g = toembeddin_time_per_vg      a      xts)
s) / len(teding_embedn(successful= leate _rsuccess       n)]
     ptioe, Excestance(sinif not ings dir e in embedgs = [e fo_embeddinulssfcce        su    
        _time
    ime - startd_t enl_time =  tota       )
   ime(e.t = timd_time          en  
          True)
  s=_exceptionasks, returner(*tgathsyncio. angs = awaitddi   embe]
         in textsr text (text) foembeddingt.generate__engine_fas[mock_ai tasks =         
   ncurrentlymbeddings co Generate e          #       
  e()
      time.timime = start_t      ast):
     _engine_fe=mock_aiturn_valu reine',ngEngIProcessi.Aenginei.rvices.a('seith patch 
        w  ]
       0)
       range(10    for i in        entities"
pics and h various toent {i} witntage cost mess"Te   f
         ts = [     tex   
   ""
     ."rmance perfo generationmbedding""Test e  "     
 ):gine_fastenmock_ai_ance(self, erformon_ptiding_generaembeddef test_  async ce
  formanrk.perytest.ma   @pcio
 ark.asyn   @pytest.m."""

 formance pering pipeline processAI"Test "e:
    "rformancocessingPetAIPrTesss ")


clah_time:.3f}savg_searc {rch time:"Average seaf     print()
       s"ime:.2f} {total_te: timint(f"Total  pr
          hes}")searctotal_ches: { sear"Total  print(f       s")
   user)} tsresull_ssfun(succehes: {let searcrenf"Concur print(        
               s"
ch_time']}sear['max_E_CONFIG{PERFORMANCs exceeds h_time:.3f}g_searc time {ave search"Averag        f        ime"], \
ax_search_t"mIG[CE_CONFRMAN< PERFOe arch_timavg_set    asser       ions
  e assertancrmrfo       # Pe      
   s)
        earch_timeean(all_sstatistics.mime = ch_t    avg_sear   mes:
     ch_tisearall_ if              
  
_searches"]cessfulesult["suc= r +ches  total_sear        mes"])
  ["search_tiresultend(_times.ext all_search        sults:
   ressful_n succeesult i       for r       
  = 0
 tal_searches       to[]
 ch_times = ear       all_sption)]
 ce(r, Excestan isinotresults if nor r in  [r fresults =sful_      succes
  e results # Analyz
              rt_time
 time - stad_ en = total_time   )
    ime(e = time.tim       end_t    
 True)
    tions=_excepasks, return(*tatherit asyncio.gawaults =        ress[:10]]
 userance_test_performor user in  fuser)hes(user_searcform_asks = [per       t
 iple usersult marches forseoncurrent  Run c  #    
         .time()
 e = timeimtart_t
        s  }
                  
 0lse_times eif searchmes) rch_tiean(seastatistics.m": earch_time  "avg_s    
          ch_times),ar(se len_searches":cessful    "suc       
     imes,": search_tarch_times  "se        d,
      ": user.iuser_id      "         
   return {       
              : {e}")
 id}{user.r user d foarch faile"Se(fnt    pri              as e:
   ception Except      ex         
               _time)
  rchend(seah_times.app    searc                   ime
 ) - start_tme(= time.tih_time  searc               
        ery).search(quearch_agentock_st m awai                      
 nt):ageck_search_lue=mourn_va, rett'archAgenridSeent.Hybi.search.agervices.ah('satcith p    w           try:
              
                  ime()
     .t = timetart_time  s         
     s)riesearch_quem.choice(y = rando     quer          :
 hes)e(num_searcangor _ in r           f       
 
     = []_times arch         se
   :hes=3)searcr, num_s(use_searcheererform_usef p    async d    
        
        ]ollow up"
      "fe",
      rtant updatpoim          "  hedule",
"meeting sc     ",
       ct alphaoje"pr 
           age",mess    "test        = [
  iessearch_quer       s
 ierch querTest sea        #    
   ch
  = mock_searde_effect rch.sint.seaearch_age     mock_s
        _result
   turn mock re          
            200)
 uniform(50,  = random.sing_time_mss.processult.stat_re  mock        s)
  .result_resultocken(ms = l_resultallt.stats.totk_resu    moc  ()
      syncMockt.stats = Ak_resuloc       m         ]
  5))
      dint(1, ndom.ranrage(in ran   for i          ry")
    } for que"Result {ient=f", cont_{i}ultk(id=f"res AsyncMoc            = [
    ultslt.res mock_resu           )
AsyncMock(k_result =    moc 
                2))
    5, 0.orm(0.0ifunep(random..sleit asyncio   awa       ng time
  rch processisea # Simulate            kwargs):
 **ch(*args,k_searf moc   async de
          t)
   enchAgybridSearck(spec=HMoent = Asyncarch_ag   mock_seays
     istic delalnt with reearch age    # Mock s
            ."""
ple usersm multierations froopearch rent s"Test concur      ""s):
  user_test_cermanfolf, perperations(search_orent_se_concur def test    asyncerformance
mark.pytest.o
    @prk.asynci @pytest.ma  ""

 lity."calabistem s sys anderationser opncurrent u""Test cos:
    "currentUserss TestCon


claf}s")ime:.3ng_trocessivg_pg time: {a processin AIragent(f"Averi        p
    2f}s")ime:._tes in {total)} messagl_resultsn(successfu {leI processed  print(f"A
                    5s"
  eeds 0.exc}s me:.3ftiing_ss {avg_procetimeg processinverage AI  f"A0.5,sing_time < vg_proces    assert a      90%"
  :.2%} below rateess_uccess rate {s"Succ f90,e > 0.ss_ratssert succe      as
      ionert assmance   # Perfor 
                lse 0
    _times erocessingf png_times) iessi(procics.meantatist_time = sssing_proce    avg   )
     asksen(tsults) / lccessful_ree = len(suess_ratucc s
                      
 ful_results] in successr rtime"] foessing_["proc= [rtimes processing_     
       ]ception)Exnstance(r,  isisults if notor r in re= [r flts _resuuccessful       sults
     yze res Anal     #
             e
      start_timime - d_tenme =     total_ti()
         time.timee =     end_tim       
     