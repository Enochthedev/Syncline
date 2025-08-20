"""
Comprehensive integration tests for all platform connectors and error scenarios.

This module tests integration between all system components and platform connectors.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
import random

from integrations.gmail_connector import GmailConnector
from integrations.slack_connector import SlackConnector
from integrations.discord_connector import DiscordConnector
from integrations.telegram_connector import TelegramConnector
from integrations.twitter_connector import TwitterConnector
from integrations.matrix_bridge_hub.hub import MatrixBridgeHub
from integrations.connector_manager import ConnectorManager
from integrations.base_connector import BaseConnector, ConnectorHealth, HealthStatus
from services.message_normalizer import MessageNormalizer
from services.ai.engine import AIProcessingEngine
ation"])", "integr", "-m"-v__, ain([__file  pytest.m
  _main__":__ == "_
if __name
nd")
ssages/secome1f} oughput:.hr {tughput:rint(f"Thro           p.2f}s")
 l_time: in {totaes messagcount}d {message_f"Processeint(  pr          
            2f}s"
ime:.l_tong: {totatoo lng took "Processi, f 5.0total_time <ert    ass         s/second"
agessme1f} ghput:.throuoo low: {Throughput t0, f"ughput > 5 thro     assert       rocessed"
 pssagesl me, "Not alsage_countmes= ssages) =ormalized_men(nleert ss      a     tions
 nce assererforma   # P
                    _time
 totalge_count / hput = messahroug       t   t
  puoughte thr Calcula       #   
     e
         start_tim_time - l_time = end        tota   
 ime.time()time = t    end_             
     
  ch_results)s.extend(batzed_message     normali      asks)
     her(*tatt asyncio.g= awai_results ch     bat         ch]
   batfor msg inmsg) e_message(alizlizer.normck_normasks = [mo         ta   _size]
     batchges[i:i +aw_messa = r       batch    ize):
     h_satc bsage_count,(0, mes range in    for i                
 
   ages = []malized_mess  nor     
     ze = 20sibatch_       
     emancer perforfor bettin batches ess    # Proc                 
time()
    time. =  start_time  :
         zer)lik_normavalue=mocrn_, retuer'alizgeNormessar.Mormalizessage_n.me'servicesch(at     with p
   troughpung throcessi Test p  # 
        e
     st_normalizfa= e_effect ge.sidsaes_mr.normalizeormalizeock_n
        m      )
             aw_data
 sg.rdata=raw_m raw_               utcnow(),
p=datetime.timestam           ,
     []s=rticipant         pa,
       ent"])["contsg.raw_datat(text=raw_mgeConten=Messa     content    
       ad_id,atform_thre=raw_msg.plm_thread_idor platf            ,
   age_idorm_mess.platfaw_msgge_id=rmessaplatform_               tform,
 w_msg.plaatform=ra  pl            sage(
  dMesizeal return Norm       
    ticipant, ParsageContente, MeslizedMessagmaorimport Nchema message_ses.servic      from     ng time
  cessi pro.001)  # 1mseep(0 asyncio.slit     awa
       sg):ize(raw_mt_normalnc def fas    asy
            zer)
aliageNormk(spec=Messocr = AsyncMk_normalize
        mocrmalizer nost # Mock fa
       
        e)essagnd(raw_m.appemessagesaw_        r
           )   }
                 mat()
 w().isofortetime.utcno: daimestamp"    "t        
        ",omxample.c0}@e% 2r{i  f"use":nder        "se        ",
    ge {i}essatest mghput ": f"Throuontent   "c            ata={
          raw_d       
    0}",read_{i % 1hput_througad_id=f"th_thre   platform     
        }",_msg_{ihputd=f"througage_issrm_melatfo      p         ",
 atform"test_plrm= platfo             sage(
  RawMesssage =      raw_me       nt):
essage_couge(mor i in ran        f
      es = []
  _messag      raw   100
sage_count =es   m   
  st messagesteerate       # Gen 
     ""
    roughput."ng th processiessage""Test m    "):
    userelf, test_oughput(sng_thr_processiest_messageef tc dsyn  amance
  rk.perfor @pytest.magration
   rk.intest.ma  @pyteo
  asyncimark.@pytest.
    
essages}"tal_m {tossages, gotted 50 me"Expec, fes == 50otal_messagssert t     aesults)
   h_rsult in fetct) for reen(resules = sum(ll_messagota      t  e count
tal messag # Verify to
               "
e:.2f}sch_timfetong: { took too lhingt fetcenrroncu< 10.0, f"C fetch_time rtse     as
   ages"fetched messonnectors ll c "Not ach_results),ult in fet> 0 for resen(result) assert all(l 
               art_time
 stme.time() - = tih_timefetc        asks)
h_tgather(*fetcasyncio.t ai = awltsetch_resu   f     nectors]
r in cononnecto c forages()rical_messhistoctor.fetch_sks = [conne fetch_ta
        time.time()time =art_   st  g
   etchin message ft concurrent Tes       #   
 "
     time:.2f}sth_ong: {auoo l took thenticationt autf"Concurren< 5.0, time h_t aut  asser"
      ccessfullyticated suors authenall connectlts), "Not uth_resut all(a asser  
       
      timet_stare.time() - time = timth_    au   th_tasks)
 ather(*auasyncio.gs = await ltauth_resu     ]
   ectorsn connctor ionnete({}) for cnticaector.authe = [conn  auth_tasks()
      e.timeme = tim_ti   start    n
 enticatioent authncurr Test co    # 
    or)
       onnect(mock_cctors.appendconne              ]
          (10)
 j in range) for            {i}"}
    form  plat from{j} f"Message tent":data={"con     raw_               ",
hread_{j}ad_id=f"thretform_t         pla        {j}",
   sg__id=f"mgeform_messa     plat             _{i}",
  f"platformtform=      pla          ge(
        RawMessa           ue = [
 .return_valsagesical_mesch_histor.fetck_connector         mo True
   value =ate.return_authenticctor.onne mock_c         
  user.id test_user_id =nector.on  mock_c        rm_{i}"
  fo = f"platlatformctor.pmock_conne            
r)eConnectospec=Bask(yncMocnnector = As   mock_co   ):
      in range(5r i    fo
     ectors = []   conntors
      connectiple mockreate mul      # C        
  "
"nnectors." coltiples across mu operationcurrent""Test con    ":
    edentials)ck_crst_user, mo(self, teonsor_operatictent_conneest_concurrsync def te
    ancrk.performapytest.ma @gration
   mark.inte   @pytest.syncio
 ytest.mark.a

    @p""egration."ects of inte aspormanc perf"""Test    
ation:tegrrformanceIntPe
class Teseded")

ver succeication neentil("Auth pytest.fa                  
 = 2:mpt =     if atte
           Exception:xcept            e  break
              succeed"
 uld hotication s"Authen, ult is Trueassert res     
           tempts"rst 2 atled fiuld have fai "Sho>= 2,tempt rt at     asse       })
    thenticate({nector.auit mock_con awat =    resul            try:
     ):
       ange(3 in rtempt    for at    n retry
enticatio auth   # Test 
     
       h_failureck_auth_wit moide_effect =ticate.sauthenr.ck_connecto     mo  
         attempt
on 3rd eed Succrue  # rn Tetu        r
    n failed")henticatioion("Autse Except        rai      
  t 2 attempts# Fail firs 2:  <=attempts  if auth_            1
pts +=tem    auth_at       empts
 al auth_attloc       non  s):
   rgs, **kwarg(*arefailuh_uth_wit def mock_a async      empts = 0
 ttth_a     aucovery
   lure retication fai Test authen    #      
    ries
   rettween bedelayief   # Brleep(0.1)yncio.s    await as           ded")
 excees Max retriet.fail("tes  py              :
    ries - 1etx_r matempt ==   if at          rror:
   TimeoutEo.t asynci   excep
         k  brea           pts"
   tem3 at first ave failedld h"Shou >= 3, ttempt    assert a           
 ()cal_messagesorih_histector.fetcit mock_connwalt = a     resu        ry:
             ties):
  x_retrrange(ma attempt in 
        fors = 5x_retrie        may logic
# Test retr            
  imeout
  tch_with_tck_feeffect = moide__messages.soricalr.fetch_hist_connecto   mock
             ttempt
n 4th aeed o  # Succ   return []
         ut")k timeoetworror("NErmeoutcio.Ti asynseai       rs
         emptattrst 3 # Fail fit <= 3:  ouneout_c tim         if   count += 1
    timeout_t
        uneout_col tim  nonloca        rgs):
  *args, **kwaith_timeout(tch_wk_feocc def m    asyn0
    t_count = ou     timeeouts
    timlate network# Simu
        "
        atform = "test_plrmtfoctor.pla  mock_conne)
      nnectoreCospec=Basock(syncMnector = Amock_con       very
 t recomeourk ti Test netwo 
        #
       """s. scenarioror recoveryer various  """Test):
       test_user(self, scenariosor_recovery_f test_errsync de    aegration
k.intpytest.maryncio
    @est.mark.as  @pyt"

  ntentssage co in merm not "Platfotext,.content.m in msgsg.platforassert m               messages:
 rmalized_in noor msg  f       ontent
    y message c # Verif               
       ssed"
 ms procetfor pla "Not all(platforms),orms == set_platf processed  assert    s}
      zed_message normalior msg inlatform fms = {msg.pssed_platfor      proced
      epresentetforms are r plall a# Verify         
        
       (*tasks)ncio.gather= await asyages sszed_me     normali     ]
  esagaw_messfor msg in rmsg) essage(malize_mmalizer.noror [mock_n =    tasks
        alizer):rmock_no=mvalue return_izer',geNormalr.Messaizee_normalices.messagservch('  with pat    rrently
  sages concu mes Process all #
           malize
     mock_norffect =ge.side_emalize_messamalizer.nor  mock_nor 
            )
       
      aw_datsg.raaw_mraw_data=r               ),
 cnow(ime.utestamp=datet       tim    ],
                      )
                 
  er"]ndw_data["sera=raw_msg.email                     ",
   Username="Test   display_                ],
      "a["sender_msg.raw_datd=rawrm_user_ifo   plat              
       m,msg.platforraw_atform=      pl                  nt(
icipa    Part          =[
      articipants       p         ]),
ontent"a["csg.raw_datw_mtext=raContent(Messagentent=   co            ,
 thread_idrm_tfopla_msg._id=rawhreadrm_tlatfo        p   _id,
     geatform_messaaw_msg.pl=rge_idatform_messa       pl      form,
   .platw_msgrm=raatfo        pl        essage(
NormalizedMeturn           ripant
  rticntent, PaeCo Messagssage,dMezelirt Normaema impochmessage_srvices.  from se      :
    e(raw_msg)ock_normaliz async def m  
             )
geNormalizerssak(spec=Meocr = AsyncM_normalizeock  m    rmalizer
   no  # Mock 
             essage)
(raw_mendges.appsa raw_mes          )
                   }
        mat()
  ow().isofor.utcn: datetime"timestamp"                
    rm}.com",latfoer{i}@{p f"us":"sender            
        latform}", from {pgessat me f"Tes":content  "           ={
       data     raw_       i}",
    m}_thread_{atfor=f"{pl_thread_idrmlatfo         p",
       m}_msg_{i}"{platford=fe_i_messag   platform          orm,
   =platf    platform           ssage(
 e = RawMeagssraw_me         rms):
   foerate(platnumrm in etfor i, pla  fo
             ]
 ssages = [     raw_me"]
   egramtel", "discord", ""slackmail", "gorms = [     platf   tforms
ifferent plaages from date mess      # Cre
  
        """ly.simultaneouslatforms ltiple p from muessagesating mggreg"""Test a      
  st_user):elf, ten(satioeg_aggrform_message_plat_multistef tec d asynration
   .integ.mark@pytest    rk.asyncio
ytest.ma  @p)

  lled_once(sert_ca.publish.asevent_bus mock_              ls
     bus calerify event  # V                
                     ion"
  dding dimens embenvalid "I 1536,mbedding) ==assert len(e                 ted"
   ry generao summa None, "Nnt"] is not"contemary[rt sum      asse            "
  tractedties ex"No enties) > 0, tin(enti  assert le           
       rify results  # Ve              
                  xt)
      tent.teconalized.orm(neddinge_emberaten_engine.gait mock_aiedding = awmb  e                 
 .text)ized.contenty(normalmmarenerate_suine.g_engmock_aiy = await summar                    nt.text)
lized.contemantities(norne.extract_egik_ai_enait moc= aw  entities                   ocessing
 pr Step 3: AI    #                     
                     })
         orm
     atfized.plrmalm": noatfor        "pl               
 d.id),(normalize_id": str  "message                 
     MALIZED", {ESSAGE_NOR"M(s.publishent_buevock_it m     awa          
     bus to event  2: Publish  # Step               
             
          == "gmail"rm atfoormalized.plassert n                 
   ge)w_messae_message(raalizmalizer.normmock_norit lized = awa       norma            age
 messmalize ep 1: Nor       # St            
                   _bus):
  =mock_eventlue, return_vaus.EventBus's.event_bcetch('servi   with pa           
  ngine):_ai_e=mocklue, return_vaingEngine'.AIProcessine.engs.aivicetch('serh pa wit       
    r):_normalizeckn_value=mo', returormalizerzer.MessageNliessage_normaservices.mth patch(' wi
       linecessing pipeest the pro     # T
           6
153 = [0.1] * ueg.return_valeddin_embne.generateai_engiock_    m     }
  st"]
     rocessing ted-to-end pts": ["En"key_poin          mary",
  ge sumest messant": "T     "conte      e = {
 alureturn_v_summary.neratei_engine.ge      mock_a    ]
  
    nce": 0.9}, "confider"e": "Sende", "valu"person":     {"type    = [
    ue valrn_tuies.rect_entitraengine.extock_ai_        mesults
processing rock AI         # M     
age
   _mess= normalized_value urne.rete_messager.normalizmaliz_normock  
              )
    a
    age.raw_datraw_messata=_d        raw    ow(),
time.utcndatetamp=times          ],
           
     )          "
    mple.com"sender@exail=       ema         ",
    ame="Sender   display_n                ",
 mple.comnder@exa"ser_id=form_useat pl        
           gmail",=" platform                   
articipant( P           ants=[
    rticip         pa
   cessing"),end pro end-to-e forsag mesxt="Test(teContentent=Message     cont
       ad_456",est_threhread_id="trm_tfoat   pl      3",
   msg_12"test__message_id=atform  pl    
      l","gmaiorm=tf pla       ssage(
    ormalizedMe= N_message alized     normicipant
   , ParteContentage, MessagizedMessormalrt Nchema impoessage_s.micesserv      from message
  rmalized  nock  # Mo
          )
        
            }mat()
    oforutcnow().isdatetime.tamp": "times          
      mple.com",sender@exa: "sender"         "
       ",rocessingend pnd-to-for esage  mesTest: "t"conten   "         ata={
    w_d         ra
   ",456test_thread_ad_id="rem_thatfor        pl   _123",
 d="test_msgge_itform_messa       pla   
  ","gmailplatform=        
    wMessage(age = Ra  raw_mess      ssage
raw mee test     # Creat        
   e)
 ssingEnginspec=AIProcecMock( Asynine =_eng_aiock        mzer)
sageNormaliock(spec=MessyncMr = Aizermal mock_no     us)
  pec=EventBcMock(ss = Asynevent_bu    mock_
    ponentsck com      # Mo      
  """
  tor to AI.onnecm crog fge processino-end messast end-t""Te       "user):
 (self, test_processingessage__mend_to_end test_async deftion
    k.integrast.mar
    @pyteiosync.aest.markpyt

    @eline."""iping page processf messtegration ost in   """Tegration:
 cessingIntegeProessa TestM
class
")
eredtriggnot miting was e li.fail("Rat    pytest       e:
     els    eak
       br   
          too early"d  triggeremitingRate lii >= 5, "rt se  as                 e):
 in str(xceeded"  limit e"Rate       if      
    ion as e:xcept Except     e)
       s(sage_mesalstoricch_hi.fetd_connector_limite  await rate                   try:

       :ge(10)for i in ran      r
  behaviomiting te list ra        # Te
        
ate_limitfetch_with_rmock_de_effect = ssages.sirical_meetch_histotor.fconnecited_e_lim        rat     
n []
   uret         r   ceeded")
imit exion("Rate lise Except     ra            5 calls
imit aftere l5:  # Ratll_count >       if ca  
    = 1ount + call_c           t
call_counnonlocal     ):
        wargs, **krgs*a_rate_limit(_fetch_withmock def async       0
 count = l_    calg
    e limitinlate rat# Simu     
    id
       er.= test_usd user_itor._conneclimited       rate_ed"
 rate_limit " =atformnector.pl_limited_con rate      onnector)
 pec=BaseCsyncMock(s = Atorecimited_conn_l      rate  ector
ted conna rate-limi   # Create             

 """lity.functiona limiting or rate connectTest"""
        est_user):ing(self, tmitlite_nector_ra_conef test
    async dnratiok.integest.mar    @pytk.asyncio
t.mar@pytes

    LTHYHEAStatus.UN == Health"].statuslatformfailing_pus["tatt health_s  asser   _status
   ealth in hm"ling_platfor"fai   assert )
     h(ealtonnector_h_cmanager.get connector_atus = awaitlth_st        heaonnector
failed cith ring witoonlth mest hea    # T        
 
   ")ng_platform("failit_connectorr.starr_managet connectowai     a):
       ion(Except.raisesytestth p wi
       g startupurinling dhandst error    # Te     
        
g_connector)ctor(failiner_connegister.retor_managt connecwai   a  r
    connectongster faili# Regi        
       
 )}
        ion failed"ticat: "Authenrror"etails={"e           d
 now(),ime.utctetheck=da     last_c
       form",ailing_plat"frm=      platfo     LTHY,
 tatus.UNHEAhSealt=Htus    sta       th(
 rHealtoue = Connecvalreturn_tatus._health_sr.geting_connecto      fail)
  d"ion faileuthenticatn("At = Exceptiode_effecenticate.sinector.auth failing_con     .id
  ert_usser_id = tesctor.uonne  failing_c   m"
   latfor "failing_platform =tor.pconnec  failing_      nnector)
ec=BaseCosyncMock(spctor = Aling_conne fai
       ctoriling conne a fa # Create 
       
       er()Managectoronn Canager =r_m connecto  
            ry."""
  recoveg andlinor handnector errst con    """Te  
  ):est_userlf, tandling(seror_hconnector_ertest_ef     async dgration
.mark.intestte
    @pyoynci.asark@pytest.m

    ALTHYatus.HEalthSttus == Hetatform].satus[plastth_al hesertas           orm}"
 for {platfs alth statu"Missing heh_status, fhealtn tform i assert pla
           ]:scord"", "diack, "sl ["gmail" in platform      for   
    atus"
   lth strted heaponectors reall con "Not == 3,us) (health_statrt len   asse)
     r_health(et_connectoer.gor_manag connect awaitstatus =lth_
        heaingonitorh m healt# Test      
     e()
     called_oncrt_cate.asseentictor.authne con      s():
     nectors.item_contor in mock, connecatform     for pled
   startre connectors a Verify all   #       
 rs()
      all_connector.start_ager_man connectowait        actors
ll connerting aTest sta  #    
      tor)
     ctor(connecr_conneregistemanager.t connector_    awai
        .items():torsonnecn mock_cnnector irm, cofo  for plators
      ectter connis    # Reg            
onnector
rm] = mock_ctfonectors[pla  mock_con         
          )onal"}
   rati": "opes={"statutailsde               now(),
 utce.eck=datetim    last_ch    
        form,orm=plat  platf       ,
       ALTHYs.HEalthStatuus=He   stat             ealth(
onnectorHvalue = Crn_s.retutatuet_health_sr.gtoconnec      mock_     = True
 _value ate.returnauthenticector.  mock_conn          id
r.d = test_useector.user_inn_cock    mo      platform
  rm = for.platnnecto     mock_co   
    seConnector)pec=Bak(sncMoctor = Asymock_connec          :
  "]ord"disc, ", "slack"in ["gmailm  for platfor     = {}
  ors ck_connect      mo
  torsk connec     # Moc
   
        r()ectorManagenn = Comanagertor_     connecnager
    manector con   # Create
     "
        "agement."fecycle mannnector li""Test co    "    tials):
ock_credent_user, m, tesgement(selfcycle_manafer_lionnectoest_cf t async de   ation
ark.integrytest.m
    @p.asynciorktest.ma @py"

   onality.""ager functi mant connector"Tes""    r:
geonnectorMana
class TestC

althy"ot heub nge Htrix BridEALTHY, "MahStatus.H== Healtatus rt health.st     asse    us()
   ealth_statb.get_htrix_humah = await alt          he
  h checkealt   # Test h              
     
  d"aileion fctne bridge conpp"WhatsAs True,  iapp_resultassert whats           onfig)
 atsapp_cpp_bridge(whwhatsact_.connetrix_hub = await maapp_resultats     wh   
         
                 }ssword"
  pat_ "tessword":as      "p  ,
        est_user"": "t"username               .com",
 mpleix.exa//matr": "https:rlr_umeserve  "ho   
           _config = {    whatsapp      nection
  p bridge conApst Whats    # Te   
            
     r.id)_id=test_useidgeHub(userxBr Matrihub =matrix_          e Hub
  x Bridg Matrind test # Create a    
        
           mock_cliente = aluturn_vss.ret_clak_clien     moc
              }
         }         }
                            }
           }
                                         ]
                           }
                                    () * 1000)
timestamptcnow()..uatetime": int(dserver_ts "origin_                                       ,
"} messageest Matrix": "T"bodyxt", ": "m.te{"msgtype: t""conten                              
          ",matrix.org@user:er": "end"s                                  ,
      e"essagoom.m: "m.rype""t                                               {
                             nts": [
   "eve                   
          ine": {"timel                           ": {
 trix.org23:maroom1         "!           : {
    join" "                s": {
   omro         "
       = {rn_value etuc.rsynent.cli    mock_
         = Truereturn_valueent.login.li mock_c       ck()
    nt = AsyncMok_clie moc       client
    rix ck Mat      # Moss:
      k_client_claocent') as mCliatrixb.hub.Mridge_hux_b.matriationsch('integr    with pat     
    """
   ration. Hub integtrix Bridgeest Ma   """T    ):
 , test_useron(self_integratidge_hub_matrix_bridef testasync    ion
 rategintmark. @pytest.ncio
   .mark.asy@pytesthy"

    ealtt hector nowitter connHEALTHY, "TalthStatus. == Heealth.statust h       asser  s()
   statu.get_health_nnectorter_cot twitth = awai   heal         eck
lth ch  # Test hea         
            "
 edon failticatiuthentter a"Twiis True, sult h_reert aut     ass
       r"])ttentials["twimock_credethenticate(ector.auitter_connwait twesult = ath_r          auion
   authenticat      # Test    
      
              )r"]
      ls["twittecredentiaials=mock_nt crede              _user.id,
 ster_id=te   us         (
    terConnectorector = Twitwitter_conn         t  r
 r connectoTwitteand test reate # C       
              ient
    mock_clurn_value =ass.retck_client_cl         mo     
   ])
       mock_dmcMock(data=[ = Asynturn_valuesages.reect_mesir_d_client.getock    m
        ow()tcntime.uat = datem.created_ock_d      mDM"
      r t Twittext = "Tes  mock_dm.te
          = "dm_123"d .idm mock_
           ck()syncModm = Amock_         es
   sagmesock direct          # M        
     user"})
  : "testsername""u123", "a={"id": ock(datncMalue = Asy_vreturnget_me.ock_client.     m
       AsyncMock()lient =    mock_c
         r client Mock Twitte  #          :
asslient_clmock_c') as .Clientector.tweepyconntwitter_grations.tech('in with pat            
"
   "ration." integnectorconest Twitter "T  ""      ):
dentialsr, mock_creuseest_on(self, t_integratictorr_connetwittedef test_    async tion
tegrak.in @pytest.mario
   k.asynctest.mar   @py

 "ched messageorm in fett platf"Incorrecm", graleform == "teat0].plmessages[ssert      a   
    egram"d from Telges fetcheo messa0, "N) > agesmessrt len(    asse        
ages()ical_messorfetch_histor.ectegram_conn tels = await  message      hing
    message fetc    # Test     
            
    lthy"not hear ram connectoelegY, "TTH.HEALlthStatus== Heaalth.status ert he         assatus()
   alth_stget_heor.m_connect telegrah = awaitlt      hea    heck
  t health ces       # T          
     
  failed"ntication am authe "Telegris True,lt  auth_resu      assert"])
      amegr["telredentialsate(mock_centicnnector.authegram_cotelt ult = awai    auth_res     cation
   est authenti       # T             
 )
         "]
      egramls["telentias=mock_cred credential            er.id,
   =test_usser_id        u  (
      nnectorelegramCoector = Tegram_conn      tel    ctor
  nnecoegram t Teld tes Create an  #   
                  ock_bot
 value = meturn_t_class.rmock_bo               }
  
                 ]      }
               
         }                   e"
 am messagTelegrTest t": ""tex                          amp()),
  mest).tie.utcnow( int(datetimdate":"                          
  "},rivatepe": "p 789, "ty":"idat": {       "ch             
        "},stuser: "te"username"789, : {"id"m": "fro                         ": 456,
   message_id         "               ": {
       "message            
         3, 12ate_id":upd    "               
     {                   sult": [
 re"              e,
  ru T "ok":              {
   =return_valuet_updates.k_bot.ge      moc    
  t"}}bo"test_": "username{ult": True, "res{"ok": alue = turn_vget_me.re   mock_bot.      ()
   AsyncMockmock_bot =      t
       am boelegrock T        # M   _class:
 bots mock_or.Bot') actm_conneegraons.teltegratith patch('in     wi  
        
 ".""rationr integam connecto"Test Telegr""
        ntials):ck_credeest_user, motion(self, tintegram_connector_est_telegrasync def tion
    ark.integratma@pytest.ncio
    symark.aytest.   @p
 "
ot healthyector ncord conn"Diss.HEALTHY, atualthSt Hestatus ==t health.      asser()
      statusget_health_ctor.d_connediscor = await thheal    ck
        h cheest healt      # T 
           "
      on faileduthenticati"Discord a rue,lt is Tauth_resuassert     
        cord"])als["disck_credentienticate(mouth.annectorscord_codit = awaiult uth_res          ation
  thentica  # Test au
                    
            )  "]
cordntials["dismock_credeentials=ed          crd,
      user.iser_id=test_    u       r(
     dConnecto = Discorectorconndiscord_         tor
   d connecst Discor teand   # Create         
           ent
  liue = mock_cs.return_valient_clasck_cl       mo    
        annel
     = mock_che turn_valunel.reget_chanck_client.   mo
         ge]mock_messa_value = [ry.returnhannel.histo     mock_c()
       nowime.utcdatet_at = .createdsagemock_mes   
         stUser".name = "Tessage.author    mock_me       ssage"
 ord mest Disctent = "Teage.conk_mess moc      6789
     345= 12.id essagemock_m         cMock()
    Asyn =mock_message     
       ck()AsyncMol = annech mock_           ges
samesd el anck chann # Mo            
    ")
       t Guildesock(name="Tlue = AsyncMeturn_va.ruild_g_client.get mock      ue
     alue = Trturn_vready.ret.is_ mock_clien       ock()
    = AsyncMck_client   mo       
   client Discord ock      # M  s:
    lasent_cliock_c mt') asscord.Clien.did_connectorcorrations.dis'integh patch(   wit    
   "
      n."" integratiod connectorst Discor """Te      s):
 edential mock_cr, test_user,lfon(setegratitor_inord_connecdiscdef test_c n
    asynegratiomark.intest.  @pytcio
  mark.asynpytest.   @

 ge"hed messaorm in fetcect platforr", "Incckorm == "sla.platfsages[0] mesassert      "
      om Slackhed frsages fetcmes, "No > 0s) geessaert len(m      ass)
      _messages(calstoritor.fetch_hiack_connecslt  awaissages =me           fetching
 st message       # Te    
      "
        t healthyonnector no, "Slack ctus.HEALTHYStaealth.status == Hhealth    assert       tatus()
  get_health_sk_connector.acait sl = aw     health  ck
      che health Test    #
                    failed"
n thenticatio"Slack au is True, uth_resultssert a a           "])
s["slack_credentiale(mockicatctor.authentnne slack_cot = awaith_resul  aut     n
     uthenticatio Test a         #  
       )
              
    "]lackls["scredentias=mock_  credential          id,
    st_user.id=teer_  us          ector(
    SlackConnr = onnectoslack_c        ctor
    k conne Slacand testeate      # Cr       
            ock_client
_value = m.returnientock_webcl     m          }
      ]
                    }
                 100"
  200.0001640995"   "ts":             
         k message",t Slacesxt": "T    "te                    123456",
": "U"user                     ",
   "message"type":                        {
                   
   [ges":sa "mes             : True,
     "ok"          e = {
   turn_valu_history.reonsrsatient.conve    mock_cli    
    est_user"}"t, "user": k": True = {"oeturn_valueest.rh_tnt.aut  mock_clie         ock()
 t = AsyncMk_clien        mocent
     WebClick Slack # Mo           bclient:
) as mock_wer.WebClient'tock_connecons.slaatiatch('integrh p  wit
              """
.rationtegconnector in"Test Slack     ""als):
    entireduser, mock_ct_n(self, tesintegratior_ctock_connet_slaf tes    async deon
tegratimark.in  @pytest.cio
  .asynt.mark@pytes    essage"

in fetched matform ect plorrncgmail", "Itform == "es[0].plassagert me  ass      l"
    maiched from Gsages fet0, "No mes> (messages) rt lense      ass()
      l_messagecaorih_histor.fetcmail_connectawait gessages =     m    tching
    ge fe messa# Test             
     "
      lthyctor not heannecol  "Gmaius.HEALTHY,tat HealthSs ==atuth.stassert heal           us()
 _health_statetnnector.git gmail_colth = awa hea          lth check
 st hea  # Te    
                
  ed"ication failuthentail arue, "Gmesult is Th_r  assert aut        mail"])
  entials["gock_crede(mhenticatnnector.autmail_cot = await g_resul  auth         ication
 Test authent  #               
            )
    "]
    "gmailcredentials[s=mock_al credenti          id,
     st_user.te    user_id=            
Connector( Gmailonnector =ail_c       gm    ctor
  connetest Gmailate and      # Cre
                   
servicek_ocvalue = mn_turk_build.remoc              }
     }
                     ded
coase64 en0"}  # Bjb250ZW5bCBWFpdCBlbVz: "VG: {"data"    "body"                  ],
                 +0000"}
 :00:00 Jan 2024 101 e": "Mon, alu"vate", "D": name       {"                 Email"},
"Test lue": , "vat"Subjec: " {"name"                     "},
  ple.comient@examcipre": , "value"me": "To"  {"na                },
      le.com"nder@examp "sevalue":m", "": "Fro  {"name                 [
      ers":ad    "he      
          yload": {      "pa
          ",t_thread_1Id": "tesadre    "th    
        sage_1",st_mes: "te    "id"     {
        urn_value =xecute.ret).get().emessages(().rvice.usersk_se      moc       }
    
       d_1"}]threat_ "tesreadId": "the_1",essag": "test_mes": [{"id    "messag          e = {
  turn_valu.recutexe.list().eages()ssusers().me_service.     mock       Mock()
nc= Asyrvice ock_se  m
           servicel API Mock Gmai #  
         _build:) as mockuild'ctor.bail_connegrations.gm'intepatch(th        wi    
 ""
    ation." integrctor Gmail conne  """Test    ):
  alsredentiser, mock_cf, test_uelegration(snnector_intail_cost_gmsync def teion
    aark.integratst.m    @pytesyncio
rk.at.matespy @"

   .""torsconnecorm  platftion of all integra""Test    "n:
ratioegIntectorormConnPlatfest

class T  }
}
         _secret"
 tokenr_access_t_twitteesecret": "token_saccess_t          "n",
  ess_toketer_acc "test_twittoken":  "access_
          ret",er_api_sec_twitt "testpi_secret":"a        key",
    ter_api_test_twitey": "api_k    "       {
 r":   "twitte      ,

        }k"/webhoolegram.com/teamples://test.exl": "http"webhook_ur    
        ,"t_tokenegram_botel"test_ken":   "bot_to       m": {
   egra     "tel},
   
        uild_id""test_gd":    "guild_i        token",
 _bot_ordsct_dies: "ten"bot_tok        "
    ord": {  "disc
       },       n"
p-tokeck-aplat-s"xapp-tes: en"tok     "app_",
       okent-slack-toxb-tes: "xken"t_to"bo         {
   ck": "sla     
   
        },resh_token"gmail_ref": "test_sh_tokenre "ref      
     cret",t_seclienest_gmail_ecret": "t  "client_s
          client_id",test_gmail_ent_id": "    "cli{
        l":   "gmain {
      uret
    r""nnectors."coplatform tials for denock cre
    """Mls():dentia mock_cree
deft.fixtur


@pytes
    )on-tenant"ati="integrnant_id        te
e=True, is_activ",
       serst UTeegration e="Intfull_nam
        com",on@example.ntegrati  email="i,
      user"ration_ame="integsern        uer",
test-usation-egr   id="int
     (User
    return sts."""ion tentegrat for i userate a test  """Cre_user():
  f test
det.fixturees


@pytort Userh.models imp.aut
from apiageMessport Rawim_schema ces.messageom servitBus
frrt Evenent_bus impo.evom servicesfr