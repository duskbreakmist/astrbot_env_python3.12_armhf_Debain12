from pathlib import Path
from setuptools import Distribution
from wheel.bdist_wheel import bdist_wheel
import runpy, os
class ArmhfDistribution(Distribution):
    def has_ext_modules(self): return True
class ArmhfWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False
    def get_tag(self): return ("cp312", "cp312", "linux_armv7l")
p=Path("setup.py")
s=p.read_text().replace('name="faiss",', 'name="faiss-cpu",')
s=s.replace('install_requires=["numpy", "packaging"],', 'install_requires=["numpy==2.4.4", "packaging"],')
s=s.replace('    zip_safe=False,', '    distclass=ArmhfDistribution,\n    cmdclass={"bdist_wheel": ArmhfWheel},\n    zip_safe=False,')
s=s.replace('long_description =', 'shutil.copyfile("/work/faiss-1.14.3/LICENSE", "faiss/LICENSE")\n\nlong_description =')
s=s.replace('"*.so", "*.pyd"', '"LICENSE", "*.so", "*.pyd"')
exec(compile(s, "setup.py", "exec"), globals())
