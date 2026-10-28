create or replace view llm_app.cortex_agent_analyst_usage_log as 
(
with agent_log as 
(select distinct 
to_varchar(RESOURCE_ATTRIBUTES:"snow.user.name")  as user_name,
to_varchar(RESOURCE_ATTRIBUTES:"snow.session.role.primary.name") as primary_role_name,
RECORD_ATTRIBUTES:"snow.ai.observability.database.name"||'.'||RECORD_ATTRIBUTES:"snow.ai.observability.schema.name"||'.'||RECORD_ATTRIBUTES:"snow.ai.observability.object.name" as agent_name,
to_varchar(RESOURCE_ATTRIBUTES:"snow.session.id") as session_id,
to_varchar(RECORD_ATTRIBUTES:"snow.ai.observability.llm.thread.id") as thread_id,
to_varchar(RECORD_ATTRIBUTES:"ai.observability.agent.first_message_in_thread") as first_message_in_thread,
to_array(parse_json(RECORD_ATTRIBUTES:"ai.observability.agent.thread_id.messages")) as thread_history,
to_varchar(RECORD_ATTRIBUTES:"ai.observability.agent.request_id") as agent_request_id,
to_varchar(RECORD_ATTRIBUTES:"ai.observability.agent.messages") as user_questions,
to_varchar(RECORD_ATTRIBUTES:"ai.observability.agent.response") as agent_responses,
ifnull(RECORD_ATTRIBUTES:"ai.observability.agent.duration"/1000,0) as response_duration_seconds,
CONVERT_TIMEZONE('UTC', 'Australia/Melbourne', start_timestamp) as question_timestamp,
CONVERT_TIMEZONE('UTC', 'Australia/Melbourne', timestamp) as logging_timestamp
--,datediff(second,question_timestamp,logging_timestamp) as response_duration
from snowflake.local.ai_observability_events
where user_questions is not null
--order by user_name, session_id, question_timestamp
)
,
analyst_log as (
select distinct
--* exclude(SOURCE, SOURCE_JSON)
user_name,
primary_role_name,
semantic_model_type,
semantic_model_name,
request_id,
to_varchar(source_json:"agent_request_id") AS agent_request_id,
latest_question,
generated_sql,
response_body,
--to_array(response_body) as response_body,
response_status_code,
feedback,
time_stamp,
ifnull(resp_meta_json:"analyst_latency_ms"/1000,0) as response_duration_seconds
from
(SELECT CONVERT_TIMEZONE('UTC', 'Australia/Melbourne', timestamp) as time_stamp,
* exclude (timestamp),
PARSE_JSON(SOURCE) as source_json
--,source_json:"agent_request_id" AS request_id
--,get(source_json,"agent_request_id") as request_id
,parse_json(response_metadata) resp_meta_json
FROM SNOWFLAKE.LOCAL.CORTEX_ANALYST_REQUESTS_V
)
where response_status_code = 200
--ORDER BY TIME_STAMP DESC, agent_request_id --source_json:"agent_request_id" --source --, request_id
)


select * 
from 
(
select a.user_name,
a.primary_role_name,
a.agent_name,
a.session_id,
a.thread_id,
a.first_message_in_thread,
a.thread_history,
a.agent_request_id,
a.user_questions,
--mode(b.semantic_model_type) as semantic_model_type,
mode(b.semantic_model_name) as semantic_model_name,
count(distinct b.request_id) as cortex_analyst_request_num,
cortex_analyst_request_num * 67/1000 as credits,
round(4.29*credits,2) as cost_usd,
a.agent_responses, 
array_agg(b.feedback) as feedback,
a.response_duration_seconds,
a.question_timestamp,
a.logging_timestamp
from agent_log a 
left join analyst_log b
on a.user_name = b.user_name
and a.agent_request_id=b.agent_request_id
and b.agent_request_id is not null
group by all
union
select distinct
user_name,
primary_role_name,
null as agent_name,
null as session_id,
null as thread_id,
null as first_message_in_thread,
null as thread_history,
agent_request_id,
latest_question as user_questions,
--semantic_model_type,
semantic_model_name,
1 as cortex_analyst_request_num,
cortex_analyst_request_num * 67/1000 as credits,
round(4.29*credits,2) as cost_usd,
--generated_sql as agent_responses,
response_body as agent_responses,
feedback,
response_duration_seconds,
time_stamp as question_timestamp,
question_timestamp as logging_timestamp
from analyst_log
where agent_request_id not in (select distinct agent_request_id from agent_log)
union
select distinct
user_name,
primary_role_name,
null as agent_name,
null as session_id,
null as thread_id,
null as first_message_in_thread,
null as thread_history,
agent_request_id,
latest_question as user_questions,
--semantic_model_type,
semantic_model_name,
1 as cortex_analyst_request_num,
cortex_analyst_request_num * 67/1000 as credits,
round(4.29*credits,2) as cost_usd,
--generated_sql as agent_responses,
response_body as agent_responses,
feedback,
response_duration_seconds,
time_stamp as question_timestamp,
question_timestamp as logging_timestamp
from analyst_log
where agent_request_id is null
)
)
;