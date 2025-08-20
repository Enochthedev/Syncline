"""
Security penetration tests for API endpoints and data protection.

This module tests security vulnerabilities, authentication bypasses,
data injection attacks, and privacy protection mechanisms.
"""

import pytest
import asyncio
import time
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
import jwt

from main import app
from api.auth.models import User
from services.security.encryption_service import EncryptionService
from services.security.audit_logger import AuditLogger
from services.ai.pii_redaction import PIIRedactor


@pytest.fixture
def malicious_payloads():
    """Common malicious payloads for injection testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE messages; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users (username) VALUES ('hacker'); --",
            "1' OR '1'='1"
        ],
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<script>alert('XSS')</script>"
        ]
    }


@pytest.fixture
def admin_user():
    """Create an admin user for privilege escalation tests."""
    return User(
        id="admin-test-user",
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        tenant_id="admin-tenant"
    )


@pytest.fixture
def test_user():
    """Create a test user for security tests."""
    return User(
        id="security-test-user",
        username="securityuser",
        email="security@example.com",
        full_name="Security Test User",
        is_active=True,
        tenant_id="security-tenant"
    )


class TestAPISecurityVulnerabilities:
    """Test API endpoints for security vulnerabilities."""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_sql_injection_protection(self, test_user, malicious_payloads):
        """Test SQL injection protection in API endpoints."""
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('api.dependencies.get_current_active_user', return_value=test_user):
                
                # Test search endpoint with SQL injection payloads
                for payload in malicious_payloads["sql_injection"]:
                    search_data = {
                        "query": payload,
                        "limit": 10
                    }
                    
                    response = await client.post("/api/v1/search/", json=search_data)
                    
                    # Should not return 500 error or expose database errors
                    assert response.status_code != 500, f"SQL injection payload caused server error: {payload}"
                    
                    # Response should not contain database error messages
                    response_text = response.text.lower()
                    dangerous_keywords = ["sql", "database", "table", "column", "syntax error"]
                   y"])ecurit-m", "s"-v", "_, ile_n([__ft.mai
    pytesn__":== "__mai__ 
if __name

uest_data}"or: {reqserver errcaused haustion "Resource ex      f                  500, \
 e !=atus_codonse.stert respss     a            rrors
   e server e not caushould        # S                
            "
    time:.2f}se_responsong: {t took too lques"Re       f            0, \
     se_time < 3rt respon      asse          me
    art_tie - ste = end_timnse_tim respo                ond
   ong to resp too lld not take Shou     #                   
         ()
       .timeme = timend_ti   e             
    t_data)quesjson=rerch/", eaapi/v1/sst("/t client.poawaiesponse =           r        ime()
  = time.ttart_time   s               uests:
   ve_reqnsie_intea in resourc_datequest for r          
                 ]
                 
   ge limit with lare queryarg # L}, ": 1000imit"l* 1000, a" : "ery"{"qu                 limit
     large# Extremely9},   99999imit":, "lt"": "tes  {"query                  sts = [
queve_retensi resource_in             
  tsequesensive re-intsourc with restTe      #      
           
          ser):_usturn_value=teuser', ret_active_.get_currentependenciesch('api.dth pat     wint:
       clie") as est="http://te_urlapp=app, bassyncClient(with A  async     
      """
    . exhaustionresourceion against est protect   """T    :
 t_user)self, testion(on_protecustice_exhaesourt_rnc def tes    asyk.security
.martest  @pycio
  synrk.amapytest.
    @rejected"
roperly load not payrge p        "La         2], \
   400, 413, 42ode in [s_c.statut response   asser            lly
 efurac grge payloads handle laject orShould re#                           
     
 oad)rge_paylson=larch/", j1/sea"/api/vost(ent.pli await ce =ns     respo                  
    
       }           ": 10
   it"lim                  tring
  MB s 1 1000000,  #": "A" *query      "            
  ayload = {e_p   larg      oad
       ge payltremely larth exwiTest    #             
               r):
  t_uselue=tesreturn_vave_user', urrent_acti.get_cependenciespatch('api.d     with         client:
") as/test="http:/p, base_url=aplient(appth AsyncCasync wi    
          
  "cks.""d atta payloast largeagainn  protectio"""Test   
     st_user):f, ten(sel_protectioyloadt_large_paync def testy
    asuriec.st.markytes
    @pasyncioest.mark.
    @pyt"
tacks.""inst DoS atotection agapr"Test ""
    ection:ceProtOfServinialass TestDecl


origins"ious ws malicallo     "CORS           \
     n, s_origi in cor notte.com"sicious-ert "mali        ass
        y risk)"(securitrigins allows all o", "CORS n != "*origissert cors_     a          _origin:
  cors  if      n")
    -Allow-Origi-Controlssces.get("Acheaderesponse._origin = r  cors          s
 origin arbitraryot allow Should n   #          
       
    headers)rs=/", heade/v1/searchons("/apient.optili await ce = respons               
  
        }          nt-Type"
ntes": "Cost-Headerequentrol-R-Co   "Access            T",
  "POS-Method":uest-Control-Req"Access           ",
     e.comious-sitalics://m: "http "Origin"           s = {
    ader          herequest
  reflight t pTes   #         
              client:
 as/test")ttp:/rl="hase_u=app, bClient(appnc with Asy async       
   ""
     rity."n secuiguratio confORS""Test C        "elf):
tion(sgurat_cors_confisync def tes    ak.security
est.mar  @pytsyncio
  k.a@pytest.mar}"

    er: {headery head securiting"Miss           f        ders, \
 .heaonseer in respead   assert h        ers:
     rity_headn secuer ihead    for      
              
         ]cy"
    Policurity-tent-SeCon "               ity",
nsport-Securct-Tra   "Stri           n",
  -Protectio"X-XSS                
ns",me-Optio"X-Fra               s",
 ptionype-Oent-Tnt-Co         "X   
    s = [eader security_h          
 eaders h securityor importanteck f      # Ch             

     t("/")it client.gesponse = awa          reent:
  ") as cli/testhttp:/se_url=", bat(app=appcClienAsynh ync wit  as
      
        ."""sentare prey headers er securit prop"Test that""
        ):ent(selfers_preseadt_security_h tes async def
   ycuritst.mark.se@pyte   io
 mark.async  @pytest.

  "ment.""rce enfoTTPSeaders and Hy hsecurit"""Test     yHeaders:
curitTestSeclass cted"


ete leak denant datass-t"Cro                             ", \
   ant-2") != "ten"tenant_idesult.get(    assert r                      "]:
  s"resultn data[r result i          fo             data:
   in"results"      if            ants
    other tenomsults freturn any renot r   # Should                      
             on()
   ponse.js  data = res                
  de == 200se.status_coonesp   assert r             
                     data)
   earch_json=ssearch/", t("/api/v1/lient.posse = await cespon        r     
       it": 10} "limata",ific dnant2 spec "te{"query":ta = earch_da       s                
                 sult
e = mock_re_valuurnsearch.retue.turn_valremock_search.                   nt data
 s-tena# No cros[]  = s resultresult.k_      moc      ()
        syncMockult = Ak_res   moc                earch:
 ock_snt') as mchAgeart.HybridSe.search.agenervices.aith patch('swi           
     t1 datarn tenanetu rshould onlych that k sear    # Moc           
             
    er):e=tenant1_usn_valuser', returve_ucticurrent_a.get_cies.dependentch('api    with pa      nt2 data
  ena access tr cannott1 uset that tenan# Tes            
            ent:
") as clistttp://te"hse_url=app=app, bant(cClie Asynync with
        as
          )     ant-2"
 ="tennt_id       tena   
  True,  is_active=
          ser", Unant 2name="Te    full_,
        om"@example.cnant2"temail=           e",
 sert2u="tenan username         _user",
  ant2 id="ten       er(
     Us_user =t2    tenan   
     )
     "
       nt-1_id="tena      tenant,
      _active=True   is       ",
  ser 1 UTenantme="     full_na
       .com",t1@exampletenan"l=    emai      r",
  enant1useme="trna         use
   t1_user",="tenanid       
     (er = Userus tenant1_       s
erent tenant from diffCreate users #          
 
     ""ants."erent tendiffion between ata isolatst d"Te       ""r):
 sef, test_uenants(sel_tn_betweenolatiois test_data_async def
    ecurityt.mark.spytesyncio
    @mark.aspytest.   @ogged"

  lents wereecurity evll s"Not a       \
      y_events), len(securitd_events) ==loggesert len(        asgged
were loall events erify       # V     
  
   action}"/{event_type}t: {en evled to loge, f"Fait Nonid is no event_ssert       at_id)
     nd(even_events.appe    logged          
 )
                   ata"}
  ": "ds={"testetail       d,
         t_user"d="teser_i   us        ,
     ty=severityveri       se
         action,  action=             t_type,
 venype=e     event_t
           vent(og_et_logger.lit audit_id = awa  even          y_events:
ritsecuerity in sev action, ent_type, for ev       
      
   = []_events  logged        
             ]
 al")
", "criticon_changednfiguratit", "cotem_even     ("sys     
  ium"),d", "meddata_updaten", "user_ficatioata_modi      ("d      h"),
", "higewedve_data_vi"sensitiaccess", "data_    (,
        medium")nied", " "access_deon",izati   ("author,
         igh")login", "h"user_cation", nti  ("authe  [
        ts = _even   security
     eventssecurity ious  Test var      #       
  ogger()
 uditLer = Aaudit_logg 
        "
       ""it logging.eness of audmpletst coTe""    "
    ):ness(selfpletecomdit_logging_test_audef 
    async curityst.mark.se   @pyteio
 ncark.asy   @pytest.m}"

 _namefieldd: {ed for fieltion fail f"Decryp        \
       text, plaincrypted ==  assert de      me)
     a, field_narypted_datpt_field(encervice.decryn_s encryptioawait= pted      decry
       ifyrypt and ver      # Dec
                 None
 ot ta.iv is nted_da encryp  assert       
    not Nonealgorithm ised_data. encrypt      assert     t None
 y_id is noed_data.kencryptssert e     a     tadata
  meencryption ave proper  Should h #        
      "
         ame}{field_neld: fi for ryptedt enc  f"Data no           ), \
   text.encode(lue != plainncrypted_vadata.eencrypted_   assert    
      textlainrom pt feren diffbeta should  daypted    # Encr
                  name)
  ld_xt, fied(plainteielcrypt_fn_service.enncryptio await e_data =ypted        encrta
    pt dacry        # Enata:
    ive_ditxt in sense, plainteamr field_n    fo 
               ]
23")
    ord_1"user_passwsword", "pas         (345"),
   uth_token_12_oa", "secret ("token           7"),
123-456", "555-"phone        ("),
    ommple.cer@exaus, ""email"     (= [
       a ve_datnsiti    se
     types dataus sensitiverioof varyption  enc     # Test       
   
 ce()yptionServie = Encron_servic  encrypti              
"
t.""ata at resensitive dryption of sTest enc""" 
       self):est(_at_roncryptist_en def tey
    asyncsecuritmark. @pytest.  .asyncio
 test.mark

    @pyt']}"case['tex in: {test_not redacted f"PII       
          \t"],e["texst_cas != teextedacted_tt r     asser     PII
  ginal ntain ori not cohouldacted text s Red          #
           xt"])
   ase["tepii(test_ct_tor.redacredact pii_wai_text = adacted    re       
 II redaction   # Test P      
            
   ']}"xtcase['tetest_pe} in: {ed_tyect {expectetto df"Failed                 \
     ted_types),dt in detect for _type in d(expectedassert any       
         ities"]:d_entcteexpeest_case[" td_type inexpecte     for           
      s]
   ed_entitiein detectr entity tity_type foy.en = [entitcted_types        dete   PII types
 ed xpectct eShould dete  #             
          "text"])
i(test_case[pir.detect_redactoi_ pi= awaities ntitected_e         deton
   I detectiest PI       # Ts:
     _test_casese in piicast_or te 
        f       ]
     
        }     "]
  ress"addtities": [ected_en"exp             45",
    123own, NY St, Anyt3 Main12ddress: "A": ext         "t    {
        
           },       ard"]
  "credit_c",: ["ssnes"ted_entiti  "expec            
  678-9012",32-1234-5 45it Card:9, Cred-45-678123SN: t": "S "tex              {
    ,
               }]
      phone", " ["email"":tiesxpected_enti        "e      -4567",
  is 555-123d phone m ane.con.doe@examplil is joh"My ema"text":                 {
     [
        t_cases = pii_tes
       ypesII t Pariouss with vTest message   #      
     ()
    PIIRedactorredactor =pii_             
 """
  cessing.n AI protion iII redacTest P"""     
   ness(self):ctiveaction_effeest_pii_redsync def t a
   rk.security.ma
    @pytest.asynciopytest.mark

    @s."""y mechanism and privactection data pro""Testcy:
    "ivaPrtectionAndDataProlass Test


c_input}"iciousmalby input: {or caused r err"Serve         f             0, \
  ode != 50status_crt response.asse           
         r errorse serveuld not causSho   #               
                    t}"
   _inpuicious{mal:  inputo maliciousponse tesd rcte  f"Unexpe                     
 ], \, 422200, 400ode in [s_ctatuponse.s assert res                   0)
acefully (20r handle gr400) or reject (ld eitheShou  #                           
            t)
icious_inpun=malrch/", jso/api/v1/seat("t.posen = await clisponse  re                  s_inputs:
iciout in mals_inpufor maliciou       
                           ]
           mbers
   nuemely large 9},  # Extr99999": mit {"li             bers
       numgative -1},  # Ne"limit":       {     n
        jectiog4j-style inm}"},  # Loap://evil.coi:ld "${jnd"query":         {    
       versalh tra,  # Patswd"}./etc/pas./.": ".{"query            a
        nary datBi"},  # 00\x01\x02ery": "\x {"qu                  
 nputng iely lo,  # Extrem000} * 10""A{"query":                     ts = [
cious_inpu        mali      uts
  cious inps malirioust with va     # Te       
                    st_user):
e=telureturn_vauser', nt_active_get_currecies.pi.dependenh patch('a    wit   t:
     lienas c) tp://test""htase_url= bapp,t(app=cCliennc with Asynasy  
             
 ion."""tization and sanit validatt inpu"Tes     "":
    test_user)(self,ontizati_saniion_andput_validatt_intesync def 
    as.securityarktest.mpy @
   iomark.asyncest.  @pyt
  ts"
apid requestected for r delimitingNo rate ount > 0, "imited_cssert rate_l a              limited
  d be rate shoulestsrequleast some  At           #        
         )
     unt(429esponses.cocount = rate_limited_         r    uests)
    Req9 Too Manys (42esponse re-limitede rat have som# Should                     
      0.01)
     cio.sleep(await asyn                 
   stming the teoid overwhelay to avall del    # Sm                    
        
        tus_code)ponse.stapend(resnses.apespo r                 ta)
  on=search_da, js/"rch/v1/seast("/apiit client.po awa  response =            
      : 1}t"", "limiquery {i}": f"test "queryata = {    search_d                rapidly
ts esend 100 requ  # S0):in range(10  for i          
      = [] responses       s
         requestapid# Simulate r                    
   :
         t_user)e=tesrn_valu, retuser'ive_urent_actet_curndencies.gpech('api.depat      with      lient:
 st") as c//tetp:ase_url="htapp, bcClient(app=Asyn async with 
            
   on."""rotectiimiting p l"Test rate      ""user):
  elf, test_ection(sng_prot_rate_limititest async def    .security
rkpytest.ma   @syncio
 mark.a @pytest.
   ."
oken[:20]}..d: {tn accepted JWT toketeipulaan        f"M      , \
      1, 403]40e in [codatus_ response.strt  asse           ns
   ulated toket manipejecd rShoul       #                 
         =headers)
", headerss/v1/messagepi/ent.get("/a await cli response =           "}
    rer {token}": f"Beaorization = {"Authders    hea          
  kens:lated_ton in manipuokeor t   f
          client://test") as"http:_url=p, basent(app=apcClieh Asynync witas              
 ]
 "
        kent.tovalid.jw       "inken
     d to # Malforme           
       "),
     m="HS256th algori",secret, "test_       }  
   sernameuser.u test_name":     "user       id,
    t_user.sub": tes   "       e({
      jwt.encod       ation
     no expiroken with  T   #    
                 56"),
orithm="HS2ret", algt_sec}, "tes          
  _user_id"ferent "difsub":     "           payload,
valid_      **        de({
      jwt.encoD
        erent user Iwith diff  # Token                    

   "),625ithm="HSgor, alet"_secrest "t         },rs=1)
   edelta(hou() - timtime.utcnow date  "exp":             ayload,
  **valid_p       
        ({wt.encode  j    oken
      ed txpir  # E          ns = [
_toketedipula       man
 ed tokensmanipulat with   # Test      
      
  256")ithm="HS", algorcretd, "test_seloae(valid_paywt.encodn = j valid_toke             
  
        }
hours=1)edelta(cnow() + time.utp": datetim        "exrname,
    ser.use": test_uername        "usr.id,
    est_use"sub": t      = {
      d valid_payloa        T token
a valid JW# Create         
        
"""alidation. and vanipulation JWT token m  """Test:
      er), test_usulation(self_token_manipf test_jwtsync de
    arityt.mark.secu  @pytesasyncio
  ytest.mark.    @p}"

dpointoint: {en endpaccess adminuser can "Non-admin        f                , \
 e == 403tatus_codnse.sert respo        ass           min users
  non-addden forbi403 Foruld return Sho         #         
                   point)
    ient.get(endawait cl = nsespo  re                ints:
  in_endpo admt inoin  for endp            
                 ]
              /"
   -logsdmin/audit/v1/a     "/api          ",
     /health/ystem/admin/s/v1pi      "/a          s/",
    usern//admii/v1  "/ap                   = [
_endpointsin   adm            s
  endpoint admin-only# Mock      
                          :
r)_usevalue=test', return_tive_userrent_acs.get_curendencie'api.depch(  with pat          
pointsnd eadmincess ing to acr user tryegulaTest r         #   
   
          ent:) as cliest""http://tbase_url=app, lient(app=ith AsyncC  async w          
 "
   alation.""ege escil privtion againstotecst pr"""Te   
     r): admin_user,_useelf, testion(stion_protectlascaege_eest_privilnc def t    asyecurity
.sest.mark
    @pytasynciotest.mark.   @py
 "
nticationout autheessible withint} accpoint {endpo"End f                   , 403], \
in [401atus_code response.st     assert        
    Forbiddenzed or 403  Unauthori return 401   # Should                    
   nt)
      et(endpoient.git cliponse = awa   res             se:
       el             json=data)
t, (endpoinclient.postwait = aonse resp              :
      "POST"od ==  if meth            
   dpoints:tected_en prodata ind, nt, methooi   for endp         
           
    ]         ne)
"GET", No", pants//partici("/api/v1              
  ne),"GET", Nods/", pi/v1/threa("/a            None),
    ", "GET", s/age1/mess"/api/v          (    "}),
  testry": ", {"queOST" "P",h/api/v1/searc    ("/           nts = [
 poiected_end        protcation
    tithout authenints wied endpootectessing pr# Test acc           
             t:
") as clienttp://testbase_url="hnt(app=app, th AsyncClie wi async         
 ""
     empts." atttion bypass authentica""Test   "    elf):
 tempts(sation_bypass_authenticattest_ async def rity
   ecu.mark.s
    @pytestyncio.asrktest.ma@py    oad}"

: {paylot sanitizedload nSS payf"Xponse_str, ot in res<script>" nassert "                         
   a).lower()nse_datrespoon.dumps(= js_str onse      resp                     onse
 sent in resprenot p are tagsscript eck that       # Ch                    
  n()nse.jso respoponse_data =       res                :
     = 200ode =.status_cif response                   ected
     ejor r sanitized ould bepayload shXSS         #             
                          ge_data)
  =messasonssages/", japi/v1/met.post("/ cliense = awaitespon  r                           
          
         k()Mocynce = Asessaglize_m_value.normaeturnnormalizer.rock_         m          zer:
     ock_normali mzer') asageNormalializer.Messe_normes.messagervicpatch('sith            w
         pointeation endessage cr  # Mock m          
                          }
                   "
   e.comexamplt@": "tes"sender                      test",
  m": "latfor       "p              ayload,
   nt": p "conte                    {
    e_data =ssag        me    ]:
        loads"ds["xss_payous_payloa in maliciload   for pay            ds
 payloa XSS on withcreatiage mess  # Test           
                    est_user):
_value=ter', returnnt_active_usget_currencies.ependeh('api.dtcpaith         wient:
    ") as clest/tttp:/="hpp, base_urlt(app=asyncClienith Anc w       asy  
 "
      ""ponses.n API res iectionrotS p""Test XS       ":
 ayloads)cious_p, maliser test_uction(self,teroxss_ptest_async def   rity
  cut.mark.se @pytesasyncio
   test.mark.@py"

    d: {payload}payloath r exposed wi erroseba"Datatext, fesponse_ord not in rkeywt sser      a                  s:
wordus_keyin dangero keyword        for      
        