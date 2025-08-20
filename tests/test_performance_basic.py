"""
Basic performance tests for message processing and concurrent operations.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime
from unittest.mock import AsyncMock, patch
import random
import string

from services.message_normalizer import MessageNormalizer
from services.message_schema import RawMessage
from api.auth.models import User


def generate_test_message(platform: str = "gmail", message_id: str = None) -> RawMessage:
    """Generate a test message for performance testing."""
    if message_id is None:
        message_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    return RawMessage(
        platform=platform,
        platform_message_id=f"{platform}_{message_id}",
        platform_thread_id=f"{platform}_thread_{message_id[:5]}",
        raw_data={
            "content": f"Test message content {message_id}",
            "sender": f"user{random.randint(1, 100)}@example.com",
            "timestamp": datetime.utcnow().isoformat(),
            "subject": f"Test Subject {message_id[:5]}"
        }
    )


class TestBasicPerformance:
    """Basic performance tests."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_message_normalization_performance(self):
        """Test message normalization performance."""
      ])rformance"pem", "", "-__, "-vin([__fileest.ma pyt":
   n__"__mainame__ == )


if __s"e:.2f}l_timtas in {tos)} messagesultul_re(successfessing: {lent proccurrenonrint(f"C 
        p
       0s"xceeds 1ime:.2f}s etotal_ting time {rocess"Total p f < 10,total_timert      asse0%"
   2%} below 9s_rate:.cesss rate {suc f"Succe> 0.90,ccess_rate t su       asser      
 ount
  _cessages) / ml_resultuccessfu len(se = success_rat      ]
 ption)Exceance(r, st isinlts if notresu for r in esults = [r_rulcessf       suc
 malizationsful nor success    # Count      
    rt_time
  e - staime = end_t total_tim)
       time(e = time.     end_tim
   
        e)ons=Trutixceprn_eetus, rask.gather(*tt asynciosults = awai
        re messages] msg in foressage(msg)alize_mrmer.no= [normaliz   tasks      ncurrently
essages co Process m    #  
         
 ime()me = time.tt_ti      star 
         r()
izeessageNormalizer = M  normal    
          nt)]
(message_couger _ in ransage() fote_test_mes[generaes =   messag  t = 50
    ssage_coun    me   
        """
 tion.lizanormage ent messacurr con"Test""       on(self):
 atint_normalizoncurrec def test_casynance
    erformytest.mark.p
    @psynciok.aart.mpytes)

    @s"_time:.3f}singavg_procesr message: {e peimf"Average tnt(
        pri:.2f}s")ime in {total_tesssagssages)} meormalized_melen(ncessed {rot(f"P   prin    
        
 "exceeds 0.1s.3f}s ing_time:essg_procavsing time {esAverage proc < 0.1, f"essing_timevg_proc   assert a
     w 90%"te:.2%} beloess_ra rate {succcess, f"Suc.90e > 0 success_ratrtasse       
        
 _count messageme /otal_tig_time = tprocessin  avg_
      nt message_cou_messages) /normalized= len(rate ccess_
        susertionsase ancerform       # P       
 e
  start_timend_time -_time =    total
     () time.timed_time =
        en
        ntinue          co
      on:pt Excepti       exced)
     zenormaliages.append(d_messzenormali         g)
       _message(msr.normalizealizeit normawarmalized =  no              y:
     tr   ges:
     g in messa     for mss = []
   essageized_malorm  nes
      ess messag    # Proc            
)
ime.time(me = ttart_ti       s   
 
     rmalizer() = MessageNo  normalizer 
            t)]
 _counssage(meangen rr _ i() fossage_meerate_tests = [genssage      me = 100
  unte_co    messag    
  