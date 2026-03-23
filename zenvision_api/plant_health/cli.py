"""Command-line interface for the Plant Health AI tool."""
import argparse
import json
import os
from .image_analyzer import analyze_image
from .video_analyzer import analyze_video


def analyze_folder(folder_path: str, output_json: str = None):
    results = {}
    for name in sorted(os.listdir(folder_path)):
        if name.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            path = os.path.join(folder_path, name)
            try:
                r = analyze_image(path)
                results[name] = r
            except Exception as e:
                results[name] = {'error': str(e)}
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(results, f, indent=2)
    return results


def main():
    parser = argparse.ArgumentParser(prog='plant-health', description='Plant Health AI - Image/Video analyzer')
    sub = parser.add_subparsers(dest='cmd')

    p_img = sub.add_parser('image', help='Analyze a single image')
    p_img.add_argument('path')
    p_img.add_argument('--out', help='Write JSON result to file')

    p_folder = sub.add_parser('folder', help='Analyze a folder of images')
    p_folder.add_argument('folder')
    p_folder.add_argument('--out')

    p_vid = sub.add_parser('video', help='Analyze a video file')
    p_vid.add_argument('path')
    p_vid.add_argument('--sample', type=int, default=5, help='Sample rate in seconds')
    p_vid.add_argument('--out', help='Write JSON result to file')

    args = parser.parse_args()
    if args.cmd == 'image':
        r = analyze_image(args.path)
        if args.out:
            with open(args.out, 'w') as f:
                json.dump(r, f, indent=2)
        else:
            print(json.dumps(r, indent=2))

    elif args.cmd == 'folder':
        r = analyze_folder(args.folder, args.out)
        if not args.out:
            print(json.dumps(r, indent=2))

    elif args.cmd == 'video':
        r = analyze_video(args.path, sample_rate=args.sample)
        if args.out:
            with open(args.out, 'w') as f:
                json.dump(r, f, indent=2)
        else:
            print(json.dumps(r, indent=2))

    else:
        parser.print_help()

if __name__ == '__main__':
    main()
