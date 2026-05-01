name: Build APK

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install buildozer
        run: |
          pip install --upgrade pip
          pip install buildozer cython
      - name: Build APK
        run: buildozer -v android debug
      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: license-plate-apk
          path: bin/*.apk
