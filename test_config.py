import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import server

class ConfigTests(unittest.TestCase):
    def test_config_drives_target_identity(self):
        with tempfile.TemporaryDirectory() as d, patch('server.SERIAL',''), patch('server.EDL_CHIP_ID',''):
            root=Path(d)
            config=root/'config.json'
            config.write_text(json.dumps({'serial':'TEST_PHONE','edl_chip_id':'abcd1234'}))
            server.configure(config)
            usb=root/'usb';usb.mkdir()
            device=usb/'1-1';device.mkdir()
            for key,value in {'idVendor':'05c6','idProduct':'9008','product':'QUSB_BULK_SN:ABCD1234','serial':'','busnum':'1','devnum':'2'}.items():
                (device/key).write_text(value)
            found=server.scan_usb(usb)
            self.assertTrue(found[0]['expected_edl'])
            (device/'product').write_text('QUSB_BULK_SN:ABCD12345')
            self.assertFalse(server.scan_usb(usb)[0]['expected_edl'])
            self.assertEqual(server.classify([],{'ok':True,'lines':['TEST_PHONE device']},{'ok':True,'lines':[]}),'adb')

    def test_invalid_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'config.json'
            for data in [{'serial':'','edl_chip_id':'ABCD'}, {'serial':'TEST','edl_chip_id':'not-hex'}, {'serial':'TEST','edl_chip_id':''}]:
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):server.configure(path)
