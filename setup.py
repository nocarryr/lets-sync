from setuptools import setup

setup(
    name = "lets-sync",
    version = "0.0.1",
    author = "Matthew Reid",
    author_email = "matt@nomadic-recording.com",
    description = ("A synchronization tool for letsencrypt data"),
    url='https://github.com/nocarryr/lets-sync',
    license='GPLv3',
    packages=['letssync'],
    include_package_data=True,
    long_description_markdown_filename='README.md',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)
