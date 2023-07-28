{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs @ {
    self,
    nixpkgs,
    ...
  }:
    inputs.flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["x86_64-linux"];

      perSystem = {
        system,
        pkgs,
        ...
      }: {
        packages.default = pkgs.poetry2nix.mkPoetryApplication {projectDir = ./.;};

        apps.default.program = "${self.packages.${system}.default.outPath}/bin/tg";

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs.python310Packages;
            [python venvShellHook]
            ++ (with pkgs; [sops yq poetry]);
          venvDir = "./.venv";
          postVenvCreation = ''
            unset SOURCE_DATE_EPOCH
            poetry env use .venv/bin/python
            poetry install
          '';
          postShellHook = ''
            unset SOURCE_DATE_EPOCH
            poetry env info
            export BOT_TOKEN=$(sops --decrypt secrets.yaml | yq -r '.tg_bot_token')
          '';

          packages = with pkgs; [
            (poetry2nix.mkPoetryEnv {projectDir = self;})
            poetry
          ];
        };
      };
    };
}
