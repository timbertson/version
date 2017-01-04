with (import <nixpkgs> {});
let
	build = pythonPackages:
		let base = import nix/default.nix {
			inherit pythonPackages lib;
			fetchFromGitHub = _ign: ./nix/local.tgz;
		}; in
		lib.overrideDerivation base (base: {
			nativeBuildInputs = base.nativeBuildInputs ++ (
				with pythonPackages; [nose nose_progressive]
			);
		});
in
lib.addPassthru (build pythonPackages) {
	py2 = build python2Packages;
	py3 = build python3Packages;
}
