class WatchVideo < Formula
  desc "Analyze videos with Claude — captions via yt-dlp, transcription via whisper.cpp"
  homepage "https://github.com/khou/watch-video"
  license "MIT"
  head "https://github.com/khou/watch-video.git", branch: "main"

  depends_on "ffmpeg"
  depends_on "whisper-cpp"
  depends_on "yt-dlp"

  def install
    libexec.install Dir["*"]
  end

  def caveats
    <<~EOS
      To activate the watch skill for Claude Code / Cursor, run:
        bash #{opt_libexec}/install.sh

      For Gemini CLI, append --gemini:
        bash #{opt_libexec}/install.sh --gemini
      and add the contents of #{opt_libexec}/prompts/gemini.md to ~/.gemini/GEMINI.md.

      Then start a new agent session and ask about a video URL.

      `brew uninstall` won't remove the ~/.claude/skills/watch symlink.
      To clean it up:
        rm ~/.claude/skills/watch
    EOS
  end

  test do
    assert_path_exists libexec/"SKILL.md"
    assert_path_exists libexec/"scripts/watch.py"
    assert_path_exists libexec/"install.sh"
  end
end
