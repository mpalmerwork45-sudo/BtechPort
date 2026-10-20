"""The local inbox retains exact inputs and exposes disconnection/cancellation."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import create_project
from authoring_contract import AuthoringError
from authoring_service import revision
import authoring_session as session

TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))


class AuthoringSession(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='btp-session-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','session-test','Session test',TOOL)
        self.folder=self.root/'session';session.create(self.doc,self.folder,brief='Preserve the handwork.',allowed_scope=['adventure.events'])

    def request(self,ops=None):
        return dict(api_version=1,request_id='session-request',project_id='session-test',expected_revision=revision(self.doc),label='Revise briefing',
            scope=['*'],operations=ops or [dict(op='object.patch',collection='events',id='beacon:welcome',changes={'text':'New briefing.'})])

    def test_submission_is_read_only_and_idempotent(self):
        before=self.doc.files();request=self.request()
        first=session.submit(self.folder,'propose',request=request,job_id='a')
        self.assertEqual(first,session.submit(self.folder,'propose',request=request,job_id='a'))
        self.assertEqual(self.doc.files(),before);self.assertEqual(session.jobs(self.folder)[0]['status'],'queued')
        request['label']='Changed input'
        with self.assertRaises(AuthoringError):session.submit(self.folder,'propose',request=request,job_id='a')

    def test_changed_import_rejects_reused_job_identity(self):
        source=self.root/'source.lua';source.write_text('return "next"')
        request=self.request([dict(op='script.import',id='session-test:script',file='source.lua',target='new.lua')])
        session.submit(self.folder,'propose',request=request,base_dir=self.root,job_id='a')
        source.write_text('return "cancel"')
        with self.assertRaisesRegex(AuthoringError,'another request or import'):session.submit(self.folder,'propose',request=request,base_dir=self.root,job_id='a')

    def test_cancel_wait_and_bounded_queue(self):
        item=session.submit(self.folder,'snapshot',job_id='snapshot')
        self.assertEqual(session.cancel(self.folder,item['id'])['status'],'cancellation_requested')
        item['status']='cancelled';session.write(session.job_folder(self.folder,item['id'])/'job.json',item)
        self.assertEqual(session.wait(self.folder,item['id'],.2)['status'],'cancelled')
        for n in range(8):session.submit(self.folder,'snapshot',job_id='queued'+str(n))
        with self.assertRaisesRegex(AuthoringError,'Eight authoring jobs'):session.submit(self.folder,'snapshot')
        with self.assertRaises(AuthoringError):session.wait(self.folder,item['id'],61)

    def test_disconnection_and_scope_are_explicit(self):
        session.submit(self.folder,'snapshot',job_id='pending')
        record=json.loads((self.folder/'session.json').read_bytes());record['heartbeat']=time.time()-60;session.write(self.folder/'session.json',record)
        self.assertEqual(session.info(self.folder)['status'],'interrupted')
        self.assertEqual(session.jobs(self.folder)[0]['status'],'interrupted')
        self.assertEqual(session.info(self.folder)['allowed_scope'],['adventure.events'])
        with self.assertRaisesRegex(AuthoringError,'Start or reconnect'):session.submit(self.folder,'snapshot')

    def test_unsafe_ids_and_embedded_session_refused(self):
        with self.assertRaises(AuthoringError):session.submit(self.folder,'snapshot',job_id='../elsewhere')
        with self.assertRaises(AuthoringError):session.create(self.doc,self.doc.root/'session')
        with self.assertRaises(AuthoringError):session.create(self.doc,self.root/'other',allowed_scope=[])

    def test_wait_returns_completed_job_without_terminal_input(self):
        item=session.submit(self.folder,'snapshot')
        def finish():
            time.sleep(.05);session.write(session.job_folder(self.folder,item['id'])/'job.json',dict(item,status='completed',result={'revision':revision(self.doc)}))
        worker=threading.Thread(target=finish);worker.start()
        result=session.wait(self.folder,item['id'],2);worker.join()
        self.assertEqual(result['status'],'completed')


if __name__=='__main__':unittest.main()
