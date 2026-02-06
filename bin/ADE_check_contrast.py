#!/usr/bin/env python3
import argparse


def get_luminance(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    r, g, b = [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def adjust(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)


def mix_colors(color1_hex, color2_hex, weight2):
    def hex_to_rgb(h):
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join([c * 2 for c in h])
        return [int(h[i : i + 2], 16) for i in (0, 2, 4)]

    rgb1, rgb2 = hex_to_rgb(color1_hex), hex_to_rgb(color2_hex)
    mixed = [round(c1 * (1 - weight2) + c2 * weight2) for c1, c2 in zip(rgb1, rgb2)]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def calculate_ratio(l1, l2):
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def check_contrast():
    parser = argparse.ArgumentParser(description="Contrast Standards Checker")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    themes = {
        "Purple": {"bg": "#0f172a", "text": "#f8fafc", "mix": "#ffffff", "limit": 0.10},
        "Dark": {"bg": "#000000", "text": "#e5e5e5", "mix": "#ffffff", "limit": 0.10},
        "Light": {"bg": "#f1f5f9", "text": "#0f172a", "mix": "#000000", "limit": 0.10},
        "Stark": {"bg": "#000000", "text": "#ffffff", "mix": "#ffffff", "limit": 0.10},
    }

    points = [0.0, 0.60, 1.0]
    output_lines = [
        "Contrast Standards Report",
        "==================================",
        "",
        "| Theme | Slider | Ratio | WCAG Compliance |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for name, data in themes.items():
        for p in points:
            intensity = (1 - p) / 0.40
            softening = max(0, min(1, data["limit"] * intensity))

            bg = mix_colors(data["bg"], data["mix"], softening)
            text = mix_colors(data["text"], bg, softening)

            ratio = calculate_ratio(get_luminance(bg), get_luminance(text))
            res = "AAA ✅" if ratio >= 7 else "AA ✅" if ratio >= 4.5 else "FAIL ❌"

            output_lines.append(f"| {name} | {int(p * 100)}% | {ratio:.2f}:1 | {res} |")

    report = "\n".join(output_lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
            print(f"Contrast report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    check_contrast()
