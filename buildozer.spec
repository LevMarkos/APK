[app]
title = Номера на фото
package.name = licensplaterecognizer
package.domain = org.yourcompany
source.dir = .
version = 0.1
requirements = python3==3.11, kivy==2.2.1, requests
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, CAMERA
android.api = 30
android.minapi = 21
log_level = 2
android.ndk = 25b
android.ndk_api = 21
android.build_tools = 30.0.3
android.accept_sdk_license = True
android.sdk_path = /home/runner/sdk
android.ndk_path = /home/runner/.buildozer/android/platform/android-ndk-r25b
android.cmdline_tools_path = /home/runner/sdk/cmdline-tools/latest

p4a.local_recipes = /home/runner/.local/share/python-for-android
p4a.branch = master

[buildozer]
