{ lib, python3Packages, fetchFromGitHub }:
let version = lib.removeSuffix "\n" (builtins.readFile ../VERSION); in
python3Packages.buildPythonPackage {
  inherit version;
  name = "version-${version}";
  src = ./..;
}
