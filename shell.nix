with (import <nixpkgs> {});
let
	base = callPackage nix/default.nix {};
in
base.overrideAttrs (base: {
	nativeBuildInputs = base.nativeBuildInputs ++ (
		with python3Packages; [nose]
	);
})
