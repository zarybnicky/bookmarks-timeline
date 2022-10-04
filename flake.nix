{
  outputs = { self, nixpkgs }: let
    pkgs = import nixpkgs {
      system = "x86_64-linux";
      overlays = [ self.overlay ];
    };
  in {
    overlay = final: prev: {
      python39 = prev.python39.override {
        packageOverrides = pyself: pysuper: {
          # pandas-datareader = pyself.buildPythonPackage rec {
          #   pname = "pandas-datareader";
          #   version = "0.9.0";
          #   src = pyself.fetchPypi {
          #     inherit pname version;
          #     sha256 = "ssvB4Wpquf8e0WeuLqkoOb6rmiCCO9AL37eBVfoE+JE=";
          #   };
          #   propagatedBuildInputs = with pyself; [];
          #   doCheck = false;
          # };
        };
      };
    };

    devShell.x86_64-linux = pkgs.mkShell {
      buildInputs = [
        pkgs.nodePackages.pyright
        (pkgs.python39.withPackages (ps: with ps; [
          pandas
          numpy
          matplotlib
          black
          pylint
        ]))
      ];
    };
  };
}
