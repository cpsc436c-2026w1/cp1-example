#!/bin/bash
# Delete everything the scripts in scripts/ create for the team (PREFIX, default t00), hourly resources first.
#
#   bash scripts/teardown.sh             # lists what it would delete and what is absent; deletes nothing
#   bash scripts/teardown.sh --dry-run   # the same
#   bash scripts/teardown.sh --yes       # deletes, then asks each service again; exit 1 if anything is left
#
# The order and the last step (each service asked again for anything with the prefix) are those of the course
# recipe cost-and-teardown (scripts/teardown.sh and teardown.toml): what bills by the hour goes first. Here that is
# the Kinesis stream (0.0165 USD an hour for its shard, price sheet, ca-central-1, 2026-11-18); the tables and the
# log group bill only what they store, the function and its mapping only when they run.
# Kept on purpose: nothing. The function's role t00-count-requests-fn is not created by these scripts (the course
# staff made it, docs/design.md, Resources) and is not deleted here; a role costs nothing.
set -uo pipefail
export AWS_PAGER=""
PREFIX=${PREFIX:-t00}
R=(--region "${AWS_REGION:-ca-central-1}")
STREAM=$PREFIX-trip-events
FUNCTION=$PREFIX-count-requests
TABLES=("$PREFIX-zone-counts" "$PREFIX-seen-events")
LOGS=/aws/lambda/$FUNCTION

case "${1:-}" in
  --yes) DO=1 ;;
  ""|--dry-run) DO=0 ;;
  *) echo "usage: bash scripts/teardown.sh [--dry-run | --yes]"; exit 2 ;;
esac

step() {   # step <what> <exists command> -- <delete command ...>
  local what=$1; shift
  local check=(); while [ "$1" != "--" ]; do check+=("$1"); shift; done; shift
  if ! "${check[@]}" >/dev/null 2>&1; then echo "absent        $what"; return; fi
  if [ $DO = 0 ]; then echo "would delete  $what"; return; fi
  if "$@" >/dev/null; then echo "deleted       $what"; else echo "FAILED        $what"; FAILED=1; fi
}
FAILED=0

# 1. Hourly: the stream.
step "Kinesis stream $STREAM (hourly)" aws kinesis describe-stream-summary "${R[@]}" --stream-name "$STREAM" -- \
  aws kinesis delete-stream "${R[@]}" --stream-name "$STREAM" --enforce-consumer-deletion
# 2. The function's event source mappings, then the function.
for uuid in $(aws lambda list-event-source-mappings "${R[@]}" --function-name "$FUNCTION" \
                --query 'EventSourceMappings[].UUID' --output text 2>/dev/null); do
  step "event source mapping $uuid ($STREAM -> $FUNCTION)" aws lambda get-event-source-mapping "${R[@]}" --uuid "$uuid" -- \
    aws lambda delete-event-source-mapping "${R[@]}" --uuid "$uuid"
done
step "Lambda function $FUNCTION" aws lambda get-function "${R[@]}" --function-name "$FUNCTION" -- \
  aws lambda delete-function "${R[@]}" --function-name "$FUNCTION"
# 3. Storage: the tables and the log group.
for table in "${TABLES[@]}"; do
  step "DynamoDB table $table" aws dynamodb describe-table "${R[@]}" --table-name "$table" -- \
    aws dynamodb delete-table "${R[@]}" --table-name "$table"
done
step "log group $LOGS" test -n "$(aws logs describe-log-groups "${R[@]}" --log-group-name-prefix "$LOGS" \
                                   --query 'logGroups[].logGroupName' --output text 2>/dev/null)" -- \
  aws logs delete-log-group "${R[@]}" --log-group-name "$LOGS"

[ $DO = 0 ] && { echo "dry run: nothing deleted (bash scripts/teardown.sh --yes deletes)"; exit 0; }

# 4. Wait for the deletes, then ask each service again for anything named with the prefix.
aws kinesis wait stream-not-exists "${R[@]}" --stream-name "$STREAM" 2>/dev/null
for table in "${TABLES[@]}"; do aws dynamodb wait table-not-exists "${R[@]}" --table-name "$table" 2>/dev/null; done
left=$( {
  aws kinesis list-streams "${R[@]}" --query "StreamNames[?starts_with(@, '$PREFIX-')]" --output text
  aws lambda list-functions "${R[@]}" --query "Functions[?starts_with(FunctionName, '$PREFIX-')].FunctionName" --output text
  aws lambda list-event-source-mappings "${R[@]}" --query "EventSourceMappings[?contains(FunctionArn, ':function:$PREFIX-')].UUID" --output text
  aws dynamodb list-tables "${R[@]}" --query "TableNames[?starts_with(@, '$PREFIX-')]" --output text
  aws logs describe-log-groups "${R[@]}" --log-group-name-prefix "/aws/lambda/$PREFIX-" --query 'logGroups[].logGroupName' --output text
} 2>&1 | tr '\t' '\n' | grep -v '^\s*$' )
if [ -n "$left" ]; then echo "still there:"; echo "$left" | sed 's/^/  /'; exit 1; fi
echo "nothing left with the prefix $PREFIX- (Kinesis streams, Lambda functions and mappings, DynamoDB tables, log groups)"
exit $FAILED
