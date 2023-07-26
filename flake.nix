{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = inputs@{
    self,
    nixpkgs,
    ...
  }: let
    supportedSystems = ["x86_64-linux"];
    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
  in {
    packages = forAllSystems (system: {
      default = pkgs.${system}.poetry2nix.mkPoetryApplication {projectDir = self;};
    });

    devShells = forAllSystems (system: {
      default = pkgs.${system}.mkShellNoCC {
        buildInputs = with pkgs.${system}.python310Packages; [ python venvShellHook ];
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

        packages = with pkgs.${system}; [
          (poetry2nix.mkPoetryEnv {projectDir = self;})
          poetry
          sops
          yq
        ];
      };
    });
  };
}
