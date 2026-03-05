{ lib, python3Packages, fetchFromGitHub }:
with python3Packages;
let version = lib.removeSuffix "\n" (builtins.readFile ../VERSION); in
buildPythonPackage {
  inherit version;
  name = "version-${version}";
  src = ./..;
  pyproject = true;
  build-system = [ setuptools ];
}
