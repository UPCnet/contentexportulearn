from setuptools import setup

setup(
    name='contentexportulearn',
    version='0.1',
    description='Example for extending collective.exportimport',
    url='https://github.com/UPCnet/contentexportulearn.git',
    author='Plone Team',
    author_email='ploneteam@upcnet.es',
    license='GPL version 2',
    packages=['contentexportulearn'],
    include_package_data=True,
    zip_safe=False,
    entry_points={'z3c.autoinclude.plugin': ['target = plone']},
    install_requires=[
        "setuptools",
        "collective.exportimport",
    ],
)
