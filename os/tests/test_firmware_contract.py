import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from firmware_contract import check_source


class FirmwareContractTest(unittest.TestCase):
    def test_source_predicate_requires_both_exact_guid_and_exact_size(self):
        # Minimal predicate excerpt from edk2-stable202402/BmBoot.c (BSD-2-Clause-Patent).
        text = '''EFI_GUID mBmAutoCreateBootOptionGuid = {
          0x8108ac4e, 0x9f11, 0x4d59, {0x85, 0x0e, 0xe2, 0x1a, 0x52, 0x2c, 0x59, 0xb2}
        };
        BOOLEAN BmIsAutoCreateBootOption (EFI_BOOT_MANAGER_LOAD_OPTION *BootOption) {
          if ((BootOption->OptionalDataSize == sizeof (EFI_GUID)) &&
              CompareGuid ((EFI_GUID *)BootOption->OptionalData, &mBmAutoCreateBootOptionGuid)) {
            return TRUE;
          } else { return FALSE; }
}
'''
        self.assertIn('OptionalDataSize', check_source(text))
        for wrong in (text.replace('0x8108ac4e', '0x8108ac4f'),
                      text.replace('OptionalDataSize ==', 'OptionalDataSize >='),
                      text.replace('CompareGuid', 'OtherComparison')):
            with self.assertRaises(AssertionError):
                check_source(wrong)
