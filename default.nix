with import <nixpkgs> {};
(callPackage nix/default.nix {}).overrideAttrs (o: {
	src = builtins.fetchGit { url = ./.; };
})
