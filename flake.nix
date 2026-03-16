{
  description = "hf - model management for local AI/ML models";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python3;
      pythonPkgs = python.pkgs;

      runtimeDeps = with pythonPkgs; [ requests ];

      testDeps = with pythonPkgs; [
        pytest
        pytest-cov
        pytest-benchmark
        hypothesis
      ];

      pythonEnv = python.withPackages (_: runtimeDeps ++ testDeps);

      hf = pythonPkgs.buildPythonApplication {
        pname = "hf";
        version = "1.0.0";
        src = ./.;
        pyproject = true;
        build-system = [ pythonPkgs.setuptools ];
        dependencies = runtimeDeps;
        doCheck = false;
        pythonImportsCheck = [ ];
      };
    in {
      packages.default = hf;

      apps.default = {
        type = "app";
        program = "${hf}/bin/hf";
      };

      checks = {
        lint = pkgs.runCommand "hf-lint" {
          nativeBuildInputs = [ pkgs.ruff ];
        } ''
          cd ${self}
          ruff check --no-cache hf.py tests/
          touch $out
        '';

        format = pkgs.runCommand "hf-format" {
          nativeBuildInputs = [ pkgs.ruff ];
        } ''
          cd ${self}
          ruff format --no-cache --check hf.py tests/
          touch $out
        '';

        typecheck = pkgs.runCommand "hf-typecheck" {
          nativeBuildInputs = [ pkgs.basedpyright pythonEnv ];
        } ''
          cp -r ${self} $TMPDIR/src
          chmod -R u+w $TMPDIR/src
          cd $TMPDIR/src
          basedpyright hf.py
          touch $out
        '';

        test = pkgs.runCommand "hf-test" {
          nativeBuildInputs = [ pythonEnv ];
        } ''
          cp -r ${self} $TMPDIR/src
          chmod -R u+w $TMPDIR/src
          cd $TMPDIR/src
          python -m pytest tests/ -x -q --cov=. --cov-report=term-missing
          touch $out
        '';

        build = hf;
      };

      devShells.default = pkgs.mkShell {
        buildInputs = [
          pythonEnv
          pkgs.ruff
          pkgs.basedpyright
          pkgs.lefthook
        ];

        shellHook = ''
          export PYTHONPATH="$PWD:$PYTHONPATH"
        '';
      };
    });
}
