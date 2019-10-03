import setuptools

from plypatch.version import __version__


setuptools.setup(
    name='plypatch3',
    version=__version__,
    description='Ply: Git-based Patch Management',
    url='https://github.com/sorrowless/ply',
    license='MIT',
    author='Rick Harris, Stan Bogatkin',
    author_email='rconradharris@gmail.com, stabog.tmb@gmail.com',
    packages=setuptools.find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
    ],
    install_requires=[],
    entry_points={
        'console_scripts': ['ply = plypatch.cli:main']
    }
)
