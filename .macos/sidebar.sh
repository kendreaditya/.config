#!/bin/bash
# .macos/sidebar.sh — Finder sidebar favorites via LSSharedFileList API
# Compiles a small Objective-C program inline using clang (no mysides dependency).
# WARNING: This resets the entire Finder Favorites sidebar section.
# Run standalone or called from setup-macos.sh (set MACOS_SETUP_RUNNING=1 to skip killall)
set -euo pipefail

echo "Configuring Finder sidebar..."

if ! command -v clang &>/dev/null; then
  echo "Warning: clang not found (install Xcode Command Line Tools). Skipping sidebar setup." >&2
  exit 0
fi

TMPFILE=$(mktemp /tmp/sidebar_setup_XXXXXX.m)
TMPBIN=$(mktemp /tmp/sidebar_setup_XXXXXX)

cat > "$TMPFILE" << 'OBJC_EOF'
#import <Foundation/Foundation.h>
#import <CoreServices/CoreServices.h>

static void addItem(LSSharedFileListRef sfl, NSString *path, NSString *label) {
    if (![[NSFileManager defaultManager] fileExistsAtPath:path]) {
        fprintf(stderr, "Sidebar: skipping '%s' (path not found)\n", [path UTF8String]);
        return;
    }
    NSURL *url = [NSURL fileURLWithPath:path];
    CFStringRef name = label ? (__bridge CFStringRef)label : NULL;
    LSSharedFileListItemRef item = LSSharedFileListInsertItemURL(
        sfl, kLSSharedFileListItemLast, name, NULL,
        (__bridge CFURLRef)url, NULL, NULL
    );
    if (item) CFRelease(item);
}

int main(void) {
    @autoreleasepool {
        LSSharedFileListRef sfl = LSSharedFileListCreate(
            kCFAllocatorDefault, kLSSharedFileListFavoriteItems, NULL
        );
        if (!sfl) {
            fprintf(stderr, "Error: could not get sidebar list ref\n");
            return 1;
        }

        LSSharedFileListRemoveAllItems(sfl);

        NSString *home = NSHomeDirectory();

        // Recents — uses a special .cannedSearch path (confirmed via API read)
        addItem(sfl,
            @"/System/Library/CoreServices/Finder.app/Contents/Resources/MyLibraries/myDocuments.cannedSearch",
            @"Recents");

        // Spritual Studies — in Google Drive; discover GDrive path dynamically
        NSString *cloudStorage = [home stringByAppendingPathComponent:@"Library/CloudStorage"];
        NSArray *cloudContents = [[NSFileManager defaultManager]
            contentsOfDirectoryAtPath:cloudStorage error:nil];
        NSString *gdrive = nil;
        for (NSString *entry in cloudContents) {
            if ([entry hasPrefix:@"GoogleDrive-"]) {
                gdrive = [cloudStorage stringByAppendingPathComponent:entry];
                break;
            }
        }

        if (gdrive) {
            addItem(sfl,
                [[gdrive stringByAppendingPathComponent:@"My Drive/Philosophy"]
                         stringByAppendingPathComponent:@"Spritual Studies"],
                @"Spritual Studies");
            addItem(sfl,
                [[gdrive stringByAppendingPathComponent:@"My Drive/Career"]
                         stringByAppendingPathComponent:@"Resume"],
                @"Resume");
        } else {
            fprintf(stderr, "Sidebar: Google Drive not found in CloudStorage, skipping GDrive items\n");
        }

        addItem(sfl, [home stringByAppendingPathComponent:@"workspace"], nil);
        addItem(sfl, @"/Applications", nil);
        addItem(sfl, [home stringByAppendingPathComponent:@"Desktop"], nil);
        addItem(sfl, [home stringByAppendingPathComponent:@"Downloads"], nil);
        addItem(sfl, [home stringByAppendingPathComponent:@"Documents"], nil);
        addItem(sfl, @"/private/tmp", @"tmp");
        // AirDrop: not a filesystem path — always accessible via Go menu, skipped here
        addItem(sfl, home, nil);  // home folder, Finder labels it with username

        CFRelease(sfl);
    }
    return 0;
}
OBJC_EOF

if ! clang -framework Foundation -framework CoreServices \
           -Wno-deprecated-declarations \
           -o "$TMPBIN" "$TMPFILE" 2>/dev/null; then
  echo "Warning: sidebar setup failed to compile (LSSharedFileList API may have been removed). Skipping." >&2
  rm -f "$TMPFILE" "$TMPBIN"
  exit 0
fi

"$TMPBIN"
rm -f "$TMPFILE" "$TMPBIN"

if [[ -z "${MACOS_SETUP_RUNNING:-}" ]]; then
  killall Finder 2>/dev/null || true
fi

echo "Finder sidebar configured."
