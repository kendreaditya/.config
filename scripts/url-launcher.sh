#!/bin/bash

# Function to display usage information
function show_usage {
  echo "Usage: url <url> [filename]"
  echo "Creates a file that when opened will redirect to the specified URL"
  echo ""
  echo "Arguments:"
  echo "  <url>       The URL to redirect to (required)"
  echo "  [filename]  Optional filename for the created file (default: derived from URL)"
}

# Check if at least one argument is provided
if [ $# -lt 1 ]; then
  show_usage
  exit 1
fi

# Check if help is requested
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  show_usage
  exit 0
fi

# Get the URL from the first argument
url="$1"

# If URL doesn't start with http:// or https://, add https://
if [[ ! "$url" =~ ^https?:// ]]; then
  url="https://$url"
fi

# Determine the filename
if [ -n "$2" ]; then
  # Use provided filename
  filename="$2"
  # Add .html extension if not present
  if [[ ! "$filename" =~ \.html$ ]]; then
    filename="${filename}.html"
  fi
else
  # Generate filename from URL (remove protocol, replace special chars with underscores)
  filename=$(echo "$url" | sed -e 's|^https\?://||' -e 's|[/:?=&]|_|g')
  # Add .html extension if not present
  if [[ ! "$filename" =~ \.html$ ]]; then
    filename="${filename}.html"
  fi
fi

# Create the HTML file
cat > "$filename" << EOF
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0; url=$url" />
  <title>Redirecting to $url</title>
</head>
<body>
  <p>Redirecting to <a href="$url">$url</a>...</p>
  <script>window.location.href = "$url";</script>
</body>
</html>
EOF

# Make file executable (might not be necessary for HTML)
chmod +x "$filename"

echo "Created file '$filename' that redirects to $url"
echo "Open this file in a web browser to go to the URL"
