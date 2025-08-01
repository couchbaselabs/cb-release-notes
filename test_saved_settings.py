import unittest
import release_note_save_settings

class MyTestCase(unittest.TestCase):

    @staticmethod
    def test_load_setting():
        release_note_saved_settings.load_database('saved_settings.db')



if __name__ == '__main__':
    unittest.main()
