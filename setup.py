from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='webircclient',
    version='0.1',
    description='IRC client with web client interface.',
    long_description = readme(),
	classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Topic :: Communications :: IRC',
      ],
    keywords = 'IRC chat webchat chat tornado HTML5 websocket client server',
    url='https://github.com/johnoneil/huplo',
    author='John O\'Neil',
    author_email='oneil.john@gmail.com',
    license='MIT',
    packages=['webircclient'],
    install_requires=[
        'cyclone',
        'twisted',
        'simplejson',
        'jsonpickle',
        'argparse'
      ],
    #scripts=[
	#],
      zip_safe=False)
