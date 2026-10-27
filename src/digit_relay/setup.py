from glob import glob

from setuptools import find_packages, setup

package_name = 'digit_relay'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='luminolous',
    maintainer_email='syauqinabil132@gmail.com',
    description='Distributed Digit Relay: 7 member nodes take turns drawing numbers in turtlesim.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            f'member_{i} = digit_relay.member_{i}:main' for i in range(1, 8)
        ],
    },
)
