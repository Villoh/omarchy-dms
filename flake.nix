{
  description = "Omarchy themes as Dank Material Shell profiles";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      forAllSystems =
        f:
        nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" ] (
          system: f nixpkgs.legacyPackages.${system}
        );
    in
    {
      packages = forAllSystems (pkgs: rec {
        omarchy-dms = pkgs.python3Packages.buildPythonApplication {
          pname = "omarchy-dms";
          version = "0.1.0";
          pyproject = true;
          src = ./.;
          build-system = [ pkgs.python3Packages.setuptools ];
          makeWrapperArgs = [
            "--prefix"
            "PATH"
            ":"
            (pkgs.lib.makeBinPath [
              pkgs.git
              pkgs.fzf
            ])
          ];
          nativeCheckInputs = [ pkgs.git ];
          checkPhase = "python -m unittest discover -s tests";
          meta.mainProgram = "omarchy-dms";
        };
        default = omarchy-dms;
      });
    };
}
