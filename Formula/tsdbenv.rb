# Formula for Homebrew - add this to your tap or homebrew-core
# https://docs.brew.sh/Formula-Cookbook

class Tsdbenv < Formula
  desc "PostgreSQL + TimescaleDB environment manager via Docker"
  homepage "https://github.com/wagnerbianchijr/tsdbenv"
  url "https://github.com/wagnerbianchijr/tsdbenv/archive/refs/heads/main.zip"
  version "0.1.0"
  sha256 "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  license "MIT"

  depends_on "python@3.11"
  depends_on "docker"

  def install
    # Create virtual environment
    venv_path = libexec/"venv"
    system "#{Formula["python@3.11"].opt_bin}/python3", "-m", "venv", venv_path

    # Upgrade pip
    bin.env_script_all_files(
      { PATH: "#{venv_path}/bin:$PATH" },
      bin/"tsdbenv_wrapper",
    )
    system "#{venv_path}/bin/pip", "install", "--upgrade", "pip", "setuptools", "wheel"

    # Install requirements
    system "#{venv_path}/bin/pip", "install", "-r", "requirements.txt"
    system "#{venv_path}/bin/pip", "install", "-e", "."

    # Create wrapper script
    (bin/"tsdbenv").write <<~EOS
      #!/bin/bash
      export PATH="#{venv_path}/bin:$PATH"
      exec python -m tsdbenv.cli "$@"
    EOS
    (bin/"tsdbenv").chmod 0o755
  end

  test do
    system "#{bin}/tsdbenv", "--version"
  end
end
