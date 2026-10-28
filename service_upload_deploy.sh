#!/bin/bash
FUNCTION=""
STAGE=""
ASSETS="assets"
QUESTIONS_FILE="retail_perf_questions.csv"
DATABASE=""
SCHEMA=""
PROJ_ROOT=""
EVAL_LOG_TBL=""
SRC="src"
EVAL_SRC="sql_eval_src"
PROCEDURE_NAME=""



upload_file_to_stage() {
    if [ -z "$PROJ_ROOT" ] || [ -z "$DATABASE" ] || [ -z "$STAGE" ] || [ -z "$SCHEMA" ]; then
        echo "Missing some required parameters to call this function"
        exit 1
    fi

    echo "Creating stage $STAGE if it doesn't already exist"
    ~/snowflake/snowsql -q "CREATE STAGE IF NOT EXISTS $STAGE DIRECTORY=(ENABLE = true);"

    echo "Uploading the file $QUESTIONS_FILE to the stage $STAGE"
    ~/snowflake/snowsql -q "PUT 'file://$PROJ_ROOT/$ASSETS/$QUESTIONS_FILE' '@$DATABASE.$SCHEMA.$STAGE' AUTO_COMPRESS=FALSE OVERWRITE = TRUE"

}


deploy_eval_pipeline_sproc() {

    if [ -z "$DATABASE" ] || [ -z "$STAGE" ] || [ -z "$SCHEMA" ] || [ -z "$PROCEDURE_NAME" ] || [ -z "$PACKAGE_NAME" ] || [ -z "$HANDLER" ] || [ -z "$EVAL_LOG_TBL" ]; then
        echo "Missing some required parameters to call this function"
        exit 1
    fi

    echo "Creating eval log table $EVAL_LOG_TBL if it doesn't already exist"
    ~/snowflake/snowsql -D database=$DATABASE -D schema=$SCHEMA -D log_table_name=$EVAL_LOG_TBL -o variable_substitution=True -f ./sql_templates/sql_eval_log_ddl.sql

    echo "Zipping the contents of the eval pipeline procedure"
    cd $PROJ_ROOT/$SRC  && zip -r $PACKAGE_NAME.zip ./$EVAL_SRC

    echo "Pushingt the zip source code to stage"
    ~/snowflake/snowsql -q "PUT 'file://$PROJ_ROOT/$SRC/$PACKAGE_NAME.zip' '@$DATABASE.$SCHEMA.$STAGE' AUTO_COMPRESS=FALSE OVERWRITE = TRUE"

    echo "Deploy the stored procedure $PROCEDURE_NAME"
    ~/snowflake/snowsql -D database=$DATABASE -D schema=$SCHEMA -D procedure_name=$PROCEDURE_NAME -D stage=$STAGE -D package_name=$PACKAGE_NAME -D handler=$HANDLER  -o variable_substitution=True -f ../sql_templates/sql_eval_sproc_ddl.sql

}



run_eval_pipeline_sproc() {
    if [ -z "$DATABASE" ] || [ -z "$STAGE" ] || [ -z "$SCHEMA" ] || [ -z "$PROCEDURE_NAME" ] || [ -z "$EVAL_LOG_TBL" ]; then
        echo "Missing some required parameters to call this function"
        exit 1
    fi

    echo "Running the Eval pipeline sproc"

    ~/snowflake/snowsql -q "CALL $DATABASE.$SCHEMA.$PROCEDURE_NAME('$SCHEMA', '$STAGE', '$QUESTIONS_FILE', '$EVAL_LOG_TBL');"

    echo "Evalution completed"

}



while [ $# -gt 0 ]; do
    case "$1" in
    --function)
        FUNCTION="$2"
        shift 2
        ;;
    --proj_root)
        PROJ_ROOT="$2"
        shift 2
        ;;
    --database)
        DATABASE="$2"
        shift 2
        ;;
    --schema)
        SCHEMA="$2"
        shift 2
        ;;
    --stage)
        STAGE="$2"
        shift 2
        ;;
    --procedure_name)
        PROCEDURE_NAME="$2"
        shift 2
        ;;
    --function_name)
        FUNCTION_NAME="$2"
        shift 2
        ;;
    --package_name)
        PACKAGE_NAME="$2"
        shift 2
        ;;
    --handler)
        HANDLER="$2"
        shift 2
        ;;
    --eval_log_table)
        EVAL_LOG_TBL="$2"
        shift 2
        ;;
    --warehouse)
        WAREHOUSE="$2"
        shift 2
        ;;
    *)
        echo "Unknown parameter: $1"
        exit 1
        ;;
    esac
done


if [[ "$FUNCTION" == "upload" ]]; then
    upload_file_to_stage
elif [[ "$FUNCTION" == "deploy_sproc" ]]; then
    deploy_eval_pipeline_sproc
elif [[ "$FUNCTION" == "run_sproc" ]]; then
    run_eval_pipeline_sproc
else
    echo "Unknown function: $FUNCTION"
    exit 1
fi