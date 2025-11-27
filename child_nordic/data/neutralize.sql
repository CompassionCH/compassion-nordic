-- Neutralize Script for Compassion Nordic database
-- ruff: noqa: E501

-- Children on hold
delete from correspondence where child_id IN (select id from compassion_child where state in ('N','I'));
delete from sponsorship_gift where child_id IN (select id from compassion_child where state in ('N','I'));
delete from recurring_contract where child_id IN (select id from compassion_child where state in ('N','I'));
delete from compassion_child where state in ('N','I');
delete from compassion_hold where state = 'active';

-- Changing parameters
update ir_config_parameter set value = 'https://stage.compassion.se' where key = 'web.external.url';
update ir_config_parameter set value = 'https://stage.compassion.se' where key = 'web.base.url';
update ir_config_parameter set value = (
    SELECT value FROM ir_config_parameter WHERE key = 'message_center_compassion.connect_api_key_stage'
    ) where key = 'message_center_compassion.connect_api_key';
update ir_config_parameter set value = (
    SELECT value FROM ir_config_parameter WHERE key = 'message_center_compassion.delivery_service_api_key_stage'
    ) where key = 'message_center_compassion.delivery_service_api_key';
update ir_config_parameter set value = (
    SELECT value FROM ir_config_parameter WHERE key = 'message_center_compassion.connect_client_stage'
    ) where key = 'message_center_compassion.connect_client';
update ir_config_parameter set value = (
    SELECT value FROM ir_config_parameter WHERE key = 'message_center_compassion.connect_secret_stage'
    ) where key = 'message_center_compassion.connect_secret';
update ir_config_parameter set value = (
    SELECT value FROM ir_config_parameter WHERE key = 'wordpress_api.api_key_stage'
    ) where key = 'wordpress_api.api_key';

-- Admin password
update res_users set password=(
    SELECT value FROM ir_config_parameter WHERE key = 'compassion_nordic.admin_password_stage'
    ) where login='admin';

-- Deactivating CRON and Automated tasks
update ir_cron set active = false;
update base_automation SET active=false;

-- Delete queue jobs
delete from queue_job where state != 'done';

-- Delete mailchimp account
DELETE FROM mailchimp_template;
DELETE FROM mailchimp_account;

-- Update FS Storage to use staging bucket
UPDATE fs_storage SET directory_path = 'stage' WHERE directory_path = 'production';
