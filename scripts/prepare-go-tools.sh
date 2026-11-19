#!/usr/bin/env bash
# Provision the shared offline Go tools on the experiment host (Linux x86_64).
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
dest="$repo/.toolchains/go"
if [[ -d "$dest" ]]; then
    "$dest/bin/protoc" --version
    "$dest/bin/protoc-gen-go" --version
    exit 0
fi
mkdir -p "$repo/.toolchains"
stage=$(mktemp -d "$repo/.toolchains/prepare.XXXXXXXX")
trap 'rm -rf -- "$stage"' EXIT
mkdir -p "$stage/tools/bin" "$stage/tools/proxy"
protoc_version=33.1
plugin_version=v1.36.11
if [[ $# -eq 0 ]]; then
    archive="$stage/protoc.zip"
    curl -fLsS "https://github.com/protocolbuffers/protobuf/releases/download/v${protoc_version}/protoc-${protoc_version}-linux-x86_64.zip" -o "$archive"
else
    archive=$(realpath -- "$1")
fi
cd "$stage"
unzip -q "$archive" 'bin/protoc' 'include/*' -d "$stage/tools"
[[ $("$stage/tools/bin/protoc" --version) == "libprotoc $protoc_version" ]]

# Copy just the published module files, never private Go cache contents.
cache=$(go env GOMODCACHE)
for item in "google.golang.org/protobuf@$plugin_version" "github.com/golang/protobuf@v1.5.0" "github.com/google/go-cmp@v0.7.0"; do
    mod=${item%@*}
    version=${item##*@}
    from="$cache/cache/download/$mod/@v"
    to="$stage/tools/proxy/$mod/@v"
    if [[ ! -f "$from/$version.ziphash" || ! -f "$from/$version.zip" || ! -f "$from/$version.mod" || ! -f "$from/$version.info" ]]; then
        go mod download "$item"
    fi
    mkdir -p "$to"
    cp "$from/$version".{info,mod,zip} "$to/"
    printf '%s\n' "$version" > "$to/list"
done
# Build the plugin from the same file proxy the experiment will use.
proxy_uri=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).as_uri())' "$stage/tools/proxy")
GOTOOLCHAIN=local GOWORK=off GOSUMDB=off GOPROXY="$proxy_uri" GOFLAGS=-modcacherw \
    GOMODCACHE="$stage/mod" GOBIN="$stage/tools/bin" \
    go install "google.golang.org/protobuf/cmd/protoc-gen-go@$plugin_version"
"$stage/tools/bin/protoc-gen-go" --version
mv -T "$stage/tools" "$dest"
