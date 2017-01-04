{ lib, pythonPackages, fetchFromGitHub }:
let srcJSON = lib.importJSON ./src.json; in
pythonPackages.buildPythonPackage rec {
  name = "version-${version}";
  version = srcJSON.inputs.version;
  src = fetchFromGitHub srcJSON.params;
}
