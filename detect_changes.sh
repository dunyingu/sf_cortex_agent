
#!/bin/bash

if [ "$BUILD_REASON" == "PullRequest" ]; then
    BASE="origin/$SYSTEM_PULLREQUEST_TARGETBRANCH"
    echo "Build Type: Pull Request"
    echo "Comparing against: $BASE"
else
    BASE="HEAD~1"
    echo "Build Type: Regular Commit"
    echo "Comparing against: $BASE"
fi


echo ""
echo "Changed files:"
echo "----------------------------------"
git diff --name-only HEAD $BASE
echo "----------------------------------"
echo ""


check_path_changes() {
    local var_name=$1
    local include_pattern=$2
    local exclude_pattern=$3
    local description=$4
    
    echo "Checking: $description"
    
    if [ -z "$exclude_pattern" ]; then
        # No exclusion pattern
        if git diff --name-only HEAD $BASE | grep  -E -q "$include_pattern"; then
            echo "Changes detected"
            echo "##vso[task.setvariable variable=$var_name]true"
        else
            echo "No changes"
            echo "##vso[task.setvariable variable=$var_name]false"
        fi
    else
        # With exclusion pattern
        if git diff --name-only HEAD $BASE | grep -E "$include_pattern" | grep -v -E -q "$exclude_pattern"; then
            echo "Changes detected (excluding: $exclude_pattern)"
            echo "##vso[task.setvariable variable=$var_name]true"
        else
            echo "No changes"
            echo "##vso[task.setvariable variable=$var_name]false"
        fi
    fi

    return 0
}


check_path_changes \
    "evalQuestionsUpdated" \
    "^assets/retail_perf_questions.csv" \
    "" \
    "Evaluation questions updated?"


check_path_changes \
    "semanticModelChanged" \
    "^assets/agent_request_config.yaml|^assets/retail_performance.yaml" \
    "" \
    "Semantic Model changes?"


check_path_changes \
    "agentCodeChange" \
    "^src/agent/|^src/semantic_model/|^src/utils|^src/api_client.py" \
    "^src/sql_eval_src/" \
    "Code changes for agents?"


check_path_changes \
    "evalCodeChange" \
    "^src/sql_eval_src/|.sql$" \
    "" \
    "Code changes for evaluation?"


exit 0