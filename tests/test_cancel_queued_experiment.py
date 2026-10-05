import pytest
from src.cancel_queued_experiment import cancel,COMMIT,PAID_STEP


def api_fixture(status='queued',conclusion='cancelled',paid=None):
    calls=[]
    def api(method,path):
        calls.append((method,path))
        if method=='POST':return None
        if path.endswith('/jobs'):return {'jobs':[{'steps':paid or []}]}
        return {'head_sha':COMMIT,'status':status if len(calls)==1 else 'completed','conclusion':conclusion}
    return api,calls


def test_exact_queued_run_cancelled_and_no_paid_step_started():
    api,calls=api_fixture();r=cancel(api,lambda _:None)
    assert r['confirmed_cancelled'] and r['paid_step_never_started']
    assert [x[0] for x in calls]==['GET','POST','GET','GET']


def test_in_progress_run_never_cancelled_or_reexecuted():
    api,calls=api_fixture(status='in_progress')
    with pytest.raises(RuntimeError):cancel(api,lambda _:None)
    assert [x[0] for x in calls]==['GET']


def test_maybe_started_paid_step_blocks_new_execution():
    api,_=api_fixture(paid=[{'name':PAID_STEP,'started_at':'2026-10-05T20:31:08Z'}])
    with pytest.raises(RuntimeError,match='may have started'):cancel(api,lambda _:None)


def test_completed_unexpectedly_is_not_replayed():
    api,_=api_fixture(conclusion='success')
    with pytest.raises(RuntimeError,match='unexpectedly'):cancel(api,lambda _:None)
