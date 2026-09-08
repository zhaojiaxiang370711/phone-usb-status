import unittest
from unittest.mock import patch
from server import classify,Monitor,PinInbox
OK={'ok':True,'lines':[]}
class StatusTests(unittest.TestCase):
    def setUp(self):
        patcher=patch("server.SERIAL","TEST_SERIAL")
        patcher.start();self.addCleanup(patcher.stop)
    def test_exact_edl_and_unknown_device(self):
        d={'vid':'05c6','pid':'9008','expected_edl':True}
        self.assertEqual(classify([d],OK,OK),'edl')
        self.assertEqual(classify([{**d,'expected_edl':False}],OK,OK),'edl_unknown')
        self.assertEqual(classify([d,d],OK,OK),'edl_unknown')
    def test_adb_authorization_and_other_phone(self):
        for wire,state in [('device','adb'),('unauthorized','adb_unauthorized'),('offline','adb_offline')]:
            self.assertEqual(classify([],{'ok':True,'lines':['TEST_SERIAL '+wire]},OK),state)
        self.assertEqual(classify([],{'ok':True,'lines':['OTHER device']},OK),'disconnected')
    def test_fastboot(self):
        self.assertEqual(classify([],OK,{'ok':True,'lines':['TEST_SERIAL fastboot']}),'fastboot')
    def test_tool_failure_not_reported_as_disconnected(self):
        self.assertEqual(classify([],{'ok':False,'lines':[]},OK),'unknown')
    def test_edl_poll_does_not_open_adb_or_fastboot(self):
        d={'vid':'05c6','pid':'9008','expected_edl':True}
        m=Monitor()
        with patch('server.scan_usb',return_value=[d]),patch('server.command_devices') as commands,patch('server.time.sleep',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):m.poll()
            commands.assert_not_called()
        self.assertEqual(m.snapshot()['state'],'edl')

class PinInboxTests(unittest.TestCase):
    def test_pin_is_single_use_and_not_exposed_by_status(self):
        now=[100.0];inbox=PinInbox(ttl_seconds=300,clock=lambda:now[0])
        inbox.put('1234')
        self.assertEqual(inbox.status(),{'pending':True,'expires_in':300})
        self.assertNotIn('1234',repr(inbox.status()))
        self.assertEqual(inbox.take(),b'1234')
        self.assertIsNone(inbox.take())
        self.assertEqual(inbox.status(),{'pending':False,'expires_in':0})
    def test_pin_expires_and_input_is_restricted(self):
        now=[10.0];inbox=PinInbox(ttl_seconds=5,clock=lambda:now[0])
        for value in ('123','123456789','12ab',1234):
            with self.assertRaises(ValueError):inbox.put(value)
        inbox.put('5678');now[0]=15.0
        self.assertIsNone(inbox.take())
if __name__=='__main__':unittest.main(verbosity=2)
