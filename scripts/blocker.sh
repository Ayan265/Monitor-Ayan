#!/bin/bash
# Helper script to block/unblock domains via /etc/hosts
# Usage: sudo ./blocker.sh [add|remove] [domain]

ACTION=$1
DOMAIN=$2

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

if [ -z "$DOMAIN" ]; then
  echo "No domain provided."
  exit 1
fi

# Clean up the domain (remove http://, https://, www., and trailing slashes)
DOMAIN=$(echo "$DOMAIN" | sed -e 's|^[^/]*//||' -e 's|^www\.||' -e 's|/.*$||')

if [ "$ACTION" == "add" ]; then
  # Check if already blocked
  if grep -q "$DOMAIN" /etc/hosts; then
    echo "Domain $DOMAIN is already blocked."
  else
    echo "127.0.0.1 $DOMAIN" >> /etc/hosts
    echo "127.0.0.1 www.$DOMAIN" >> /etc/hosts
    echo "Blocked $DOMAIN"
  fi
elif [ "$ACTION" == "remove" ]; then
  # Remove entries for this domain
  sed -i "/$DOMAIN/d" /etc/hosts
  echo "Unblocked $DOMAIN"
else
  echo "Invalid action. Use 'add' or 'remove'."
  exit 1
fi
