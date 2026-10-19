import json, unittest
from PIL import Image,ImageChops,ImageDraw
from validate_registration import HERE, measure

class RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template=json.loads((HERE/'template.json').read_text())
        cls.image=Image.open(HERE/'blank_six_view_grid.png').convert('RGB')
    def test_exact_blank_registers_only(self):
        result=measure(self.image,self.template)
        self.assertTrue(result['registration_pass'])
        self.assertEqual(result['visible_fiducials'],24)
        self.assertEqual(result['max_error_px'],0)
    def test_shift_rejected(self):
        result=measure(ImageChops.offset(self.image,5,0),self.template)
        self.assertFalse(result['registration_pass'])
    def test_wrong_canvas_rejected(self):
        result=measure(self.image.resize((1520,1024)),self.template)
        self.assertFalse(result['registration_pass'])
    def test_missing_marker_rejected(self):
        im=self.image.copy();ImageDraw.Draw(im).rectangle((50,34,62,46),fill='white')
        result=measure(im,self.template)
        self.assertFalse(result['registration_pass'])
        self.assertEqual(result['visible_fiducials'],23)
    def test_actual_candidate_detects_top_deformation(self):
        result=measure(Image.open(HERE/'generated_candidate_r01.png'),self.template)
        self.assertFalse(result['registration_pass'])
        self.assertEqual(result['visible_fiducials'],24)
        self.assertGreater(result['max_error_px'],129)
        self.assertGreater(result['diagnostic_affine_fits']['top']['anisotropy'],1.3)

if __name__=='__main__':unittest.main()
