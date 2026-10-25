#!/usr/bin/env bash
# 本机打安卓正式包：生成原生工程 → Gradle 出 release 包 → 用正式密钥重新签名。
# 用法：bash scripts/build-apk.sh
#   连本地开发后端：EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000/api/v1 bash scripts/build-apk.sh
# 签名密钥默认在 ~/.huzhi-oa/（不进仓库）；丢失后已安装的用户无法覆盖升级，务必备份。
set -euo pipefail

cd "$(dirname "$0")/.."
KEY_DIR="${HUZHI_OA_KEY_DIR:-$HOME/.huzhi-oa}"
PROPS="$KEY_DIR/keystore.properties"
[ -f "$PROPS" ] || { echo "缺少签名配置 $PROPS" >&2; exit 1; }
STORE_FILE="$(grep '^storeFile=' "$PROPS" | cut -d= -f2-)"
KEY_ALIAS="$(grep '^keyAlias=' "$PROPS" | cut -d= -f2-)"
STORE_PASSWORD="$(grep '^storePassword=' "$PROPS" | cut -d= -f2-)"

export JAVA_HOME="${JAVA_HOME:-$(ls -d "$HOME"/.local/jdk-21*/Contents/Home 2>/dev/null | head -1)}"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export PATH="$HOME/.local/node/bin:$JAVA_HOME/bin:$PATH"
BUILD_TOOLS="$ANDROID_HOME/build-tools/$(ls "$ANDROID_HOME/build-tools" | sort -V | tail -1)"

VERSION="$(node -p 'require("./package.json").version')"
API="${EXPO_PUBLIC_API_BASE_URL:-https://huzhilawfirm.com/api/v1}"
SUFFIX=""
[[ "$API" == https://huzhilawfirm.com/* ]] || SUFFIX="-dev"

npx expo prebuild --platform android --clean --no-install
# 只打真机架构（arm64 / 老 32 位 ARM），不带 x86 模拟器库，安装包小一半以上。
(cd android && ./gradlew --no-daemon -q assembleRelease -PreactNativeArchitectures=arm64-v8a,armeabi-v7a)

mkdir -p dist
OUT="dist/huzhi-oa-$VERSION$SUFFIX.apk"
"$BUILD_TOOLS/apksigner" sign --ks "$STORE_FILE" --ks-key-alias "$KEY_ALIAS" --ks-pass "pass:$STORE_PASSWORD" \
  --out "$OUT" android/app/build/outputs/apk/release/app-release.apk
"$BUILD_TOOLS/apksigner" verify --print-certs "$OUT" | grep -E "SHA-256|Signer #1 certificate DN"
echo "接口地址：$API"
echo "安装包：$(pwd)/$OUT ($(du -h "$OUT" | cut -f1))"
