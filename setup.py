from setuptools import setup, find_packages

setup(
    name='meridian',
    version='0.1.0',
    description='Autonomous AI toolkit — tools for continuous operation on Linux',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='KometzRobot',
    author_email='kometzrobot@proton.me',
    url='https://github.com/KometzRobot/project',
    packages=find_packages(),
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Topic :: System :: Monitoring',
        'Topic :: Internet',
    ],
    keywords='autonomous ai agent tools linux email github',
)
