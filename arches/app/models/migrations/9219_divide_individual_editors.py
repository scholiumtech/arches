import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("models", "9259_performance_fixes"),
    ]

    divide_bulk_data_editor = """
        DELETE FROM load_staging WHERE loadid IN (SELECT loadid FROM load_event WHERE etl_module_id = '6d0e7625-5792-4b83-b14b-82f603913706');
        DELETE FROM load_event WHERE etl_module_id = '6d0e7625-5792-4b83-b14b-82f603913706';
        DELETE FROM etl_modules WHERE etlmoduleid = '6d0e7625-5792-4b83-b14b-82f603913706';

        INSERT INTO etl_modules(
            etlmoduleid,name,description,etl_type,component,componentname,modulename,classname,config,icon,slug
        )
        VALUES
            (
                '80fc7aab-cbd8-4dc0-b55b-5facac4cd157',
                'Bulk Data Editor - Trim',
                'Remove Leading and Trailing Spaces',
                'edit',
                'views/components/etl_modules/bulk-trim-editor',
                'bulk-trim-editor',
                'base_data_editor.py',
                'BaseDataEditor',
                '{"bgColor": "#7EC8E3", "circleColor": "#AEC6CF", "show": true}',
                'fa fa-edit',
                'bulk-trim-editor'
            ),
            (
                'e4169b44-124a-4ff6-bd11-5521901f98a7',
                'Bulk Data Editor - Captalize',
                'Capitalize the First Letter of Every Words (Title Case)',
                'edit',
                'views/components/etl_modules/bulk-capitalize-editor',
                'bulk-capitalize-editor',
                'base_data_editor.py',
                'BaseDataEditor',
                '{"bgColor": "#7EC8E3", "circleColor": "#AEC6CF", "show": true}',
                'fa fa-edit',
                'bulk-capitalize-editor'
            ),
            (
                '5bd600f0-0896-46fa-a224-8602ebf45048',
                'Bulk Data Editor - Upper Case',
                'Convert All the Words into Upper Case',
                'edit',
                'views/components/etl_modules/bulk-uppercase-editor',
                'bulk-uppercase-editor',
                'base_data_editor.py',
                'BaseDataEditor',
                '{"bgColor": "#7EC8E3", "circleColor": "#AEC6CF", "show": true}',
                'fa fa-edit',
                'bulk-uppercase-editor'
            ),
            (
                '11e3cf3e-8530-43c2-9eb4-e7bf7aa00f17',
                'Bulk Data Editor - Lower Case',
                'Convert All the Words into Lower Case',
                'edit',
                'views/components/etl_modules/bulk-lowercase-editor',
                'bulk-lowercase-editor',
                'base_data_editor.py',
                'BaseDataEditor',
                '{"bgColor": "#7EC8E3", "circleColor": "#AEC6CF", "show": true}',
                'fa fa-edit',
                'bulk-lowercase-editor'
            ),
            (
                '9079b83c-e22b-4fdc-a22e-74487ee7b7f3',
                'Bulk Data Editor - Replace',
                'Replace All the Matching Words with a New Word',
                'edit',
                'views/components/etl_modules/bulk-replace-editor',
                'bulk-replace-editor',
                'base_data_editor.py',
                'BaseDataEditor',
                '{"bgColor": "#7EC8E3", "circleColor": "#AEC6CF", "show": true}',
                'fa fa-edit',
                'bulk-replace-editor'
            );
    """
    combine_bulk_data_editor = """
        DELETE FROM load_staging WHERE loadid IN (SELECT loadid FROM load_event WHERE etl_module_id IN (
            '80fc7aab-cbd8-4dc0-b55b-5facac4cd157',
            'e4169b44-124a-4ff6-bd11-5521901f98a7',
            '5bd600f0-0896-46fa-a224-8602ebf45048',
            '11e3cf3e-8530-43c2-9eb4-e7bf7aa00f17',
            '9079b83c-e22b-4fdc-a22e-74487ee7b7f3'
        ));
        DELETE FROM load_event WHERE etl_module_id IN (
            '80fc7aab-cbd8-4dc0-b55b-5facac4cd157',
            'e4169b44-124a-4ff6-bd11-5521901f98a7',
            '5bd600f0-0896-46fa-a224-8602ebf45048',
            '11e3cf3e-8530-43c2-9eb4-e7bf7aa00f17',
            '9079b83c-e22b-4fdc-a22e-74487ee7b7f3'
        );
        DELETE FROM etl_modules WHERE etlmoduleid IN (
            '80fc7aab-cbd8-4dc0-b55b-5facac4cd157',
            'e4169b44-124a-4ff6-bd11-5521901f98a7',
            '5bd600f0-0896-46fa-a224-8602ebf45048',
            '11e3cf3e-8530-43c2-9eb4-e7bf7aa00f17',
            '9079b83c-e22b-4fdc-a22e-74487ee7b7f3'
        );

        INSERT INTO etl_modules(
            etlmoduleid,name,description,etl_type,component,componentname,modulename,classname,config,icon,slug
        )
        VALUES (
            '6d0e7625-5792-4b83-b14b-82f603913706',
            'Bulk Data Editor',
            'Edit Existing Data in Arches',
            'edit',
            'views/components/etl_modules/bulk-data-editor',
            'bulk-data-editor',
            'bulk_data_editor.py',
            'BulkDataEditor',
            '{"bgColor": "#7EC8E3", "circleColor": "#AEC6CF", "show": true}',
            'fa fa-edit',
            'bulk-data-editor'
        );
    """

    update_edit_function = """
        CREATE OR REPLACE FUNCTION __arches_edit_staged_data(
            load_id uuid,
            graph_id uuid,
            node_id uuid,
            language_code text,
            operation text,
            old_text text,
            new_text text
        )
        RETURNS VOID
        LANGUAGE 'plpgsql'
        AS $$
            DECLARE
                node_ids uuid[];
                language_codes text[];
                tile_id uuid;
                tile_data jsonb;
                nodegroup_id uuid;
                parenttile_id uuid;
                resourceinstance_id uuid;
                data_type text;
                transform_sql text;
                updated_staged_data jsonb;
                updated_value jsonb;
                staged_record record;
                _key text;
                _value text;
            BEGIN
                IF node_id IS NULL THEN
                    node_ids := ARRAY(
                        SELECT nodeid
                        FROM nodes
                        WHERE datatype = 'string'
                        AND graphid = graph_id
                    );
                ELSE
                    node_ids = ARRAY[node_id];
                END IF;

                IF language_code IS NULL THEN
                    language_codes := ARRAY(SELECT code FROM languages);
                ELSE
                    language_codes = ARRAY[language_code];
                END IF;

                FOR staged_record IN (SELECT value, tileid FROM load_staging WHERE loadid = load_id) LOOP
                    updated_staged_data = '{}'::jsonb;
                    FOR _key, _value IN SELECT * FROM jsonb_each(staged_record.value) LOOP
                        SELECT datatype INTO data_type FROM nodes WHERE nodeid = _key::uuid;
                        updated_value = _value::jsonb;
                        IF _key::uuid = ANY(node_ids) THEN
                            IF data_type = 'string' THEN
                                FOREACH language_code IN ARRAY language_codes LOOP
                                    updated_value = jsonb_set(
                                        updated_value,
                                        FORMAT('{%s, "value"}', language_code)::text[],
                                        CASE operation
                                            WHEN 'replace' THEN
                                                FORMAT('"%s"', REPLACE(updated_value -> language_code ->> 'value', old_text, new_text))::jsonb
                                            WHEN 'replace_i' THEN
                                                FORMAT('"%s"', REGEXP_REPLACE(updated_value -> language_code ->> 'value', old_text, new_text, 'i'))::jsonb
                                            WHEN 'trim' THEN
                                                FORMAT('"%s"', TRIM(updated_value -> language_code ->> 'value'))::jsonb
                                            WHEN 'capitalize' THEN
                                                FORMAT('"%s"', INITCAP(updated_value -> language_code ->> 'value'))::jsonb
                                            WHEN 'capitalize_trim' THEN
                                                FORMAT('"%s"', TRIM(INITCAP(updated_value -> language_code ->> 'value')))::jsonb
                                            WHEN 'upper' THEN
                                                FORMAT('"%s"', UPPER(updated_value -> language_code ->> 'value'))::jsonb
                                            WHEN 'upper_trim' THEN
                                                FORMAT('"%s"', TRIM(UPPER(updated_value -> language_code ->> 'value')))::jsonb
                                            WHEN 'lower' THEN
                                                FORMAT('"%s"', LOWER(updated_value -> language_code ->> 'value'))::jsonb
                                            WHEN 'lower_trim' THEN
                                                FORMAT('"%s"', TRIM(LOWER(updated_value -> language_code ->> 'value')))::jsonb
                                            ELSE
                                                FORMAT('"%s"', updated_value -> language_code ->> 'value')::jsonb
                                        END
                                    );
                                -- ELSEIF for other datatypes
                                END LOOP;
                            END IF;
                        END IF;
                        updated_staged_data = jsonb_set(
                            updated_staged_data,
                            FORMAT('{%s}', _key)::text[],
                            jsonb_build_object(
                                'notes', '',
                                'valid', true,
                                'source', 'bulk_edit',
                                'datatype', data_type,
                                'value', updated_value
                            ),
                            true
                        );
                        UPDATE load_staging
                        SET value = updated_staged_data
                        WHERE loadid = load_id AND tileid = staged_record.tileid;
                    END LOOP;
                END LOOP;
            END;
        $$;
    """
    revert_edit_function = """
        CREATE OR REPLACE FUNCTION __arches_edit_staged_data(
            load_id uuid,
            graph_id uuid,
            node_id uuid,
            language_code text,
            operation text,
            old_text text,
            new_text text
        )
        RETURNS VOID
        LANGUAGE 'plpgsql'
        AS $$
            DECLARE
                node_ids uuid[];
                language_codes text[];
                tile_id uuid;
                tile_data jsonb;
                nodegroup_id uuid;
                parenttile_id uuid;
                resourceinstance_id uuid;
                data_type text;
                transform_sql text;
                updated_staged_data jsonb;
                updated_value jsonb;
                staged_record record;
                _key text;
                _value text;
            BEGIN
                IF node_id IS NULL THEN
                    node_ids := ARRAY(
                        SELECT nodeid
                        FROM nodes
                        WHERE datatype = 'string'
                        AND graphid = graph_id
                    );
                ELSE
                    node_ids = ARRAY[node_id];
                END IF;

                IF language_code IS NULL THEN
                    language_codes := ARRAY(SELECT code FROM languages);
                ELSE
                    language_codes = ARRAY[language_code];
                END IF;

                FOR staged_record IN (SELECT value, tileid FROM load_staging WHERE loadid = load_id) LOOP
                    updated_staged_data = '{}'::jsonb;
                    FOR _key, _value IN SELECT * FROM jsonb_each(staged_record.value) LOOP
                        SELECT datatype INTO data_type FROM nodes WHERE nodeid = _key::uuid;
                        updated_value = _value::jsonb;
                        IF _key::uuid = ANY(node_ids) THEN
                            IF data_type = 'string' THEN
                                FOREACH language_code IN ARRAY language_codes LOOP
                                    updated_value = jsonb_set(
                                        updated_value,
                                        FORMAT('{%s, "value"}', language_code)::text[],
                                        CASE operation
                                            WHEN 'replace' THEN
                                                FORMAT('"%s"', REPLACE(updated_value -> language_code ->> 'value', old_text, new_text))::jsonb
                                            WHEN 'upper' THEN
                                                FORMAT('"%s"', UPPER(updated_value -> language_code ->> 'value'))::jsonb
                                            WHEN 'lower' THEN
                                                FORMAT('"%s"', LOWER(updated_value -> language_code ->> 'value'))::jsonb
                                            WHEN 'trim' THEN
                                                FORMAT('"%s"', TRIM(updated_value -> language_code ->> 'value'))::jsonb
                                            WHEN 'capitalize' THEN
                                                FORMAT('"%s"', INITCAP(updated_value -> language_code ->> 'value'))::jsonb
                                            ELSE
                                                FORMAT('"%s"', updated_value -> language_code ->> 'value')::jsonb
                                        END
                                    );
                                -- ELSEIF for other datatypes
                                END LOOP;
                            END IF;
                        END IF;
                        updated_staged_data = jsonb_set(
                            updated_staged_data,
                            FORMAT('{%s}', _key)::text[],
                            jsonb_build_object(
                                'notes', '',
                                'valid', true,
                                'source', 'bulk_edit',
                                'datatype', data_type,
                                'value', updated_value
                            ),
                            true
                        );
                        UPDATE load_staging
                        SET value = updated_staged_data
                        WHERE loadid = load_id AND tileid = staged_record.tileid;
                    END LOOP;
                END LOOP;
            END;
        $$;
    """

    operations = [
        migrations.AddField(
            model_name="loadevent",
            name="taskid",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunSQL(
            divide_bulk_data_editor,
            combine_bulk_data_editor,
        ),
        migrations.RunSQL(
            update_edit_function,
            revert_edit_function,
        ),
    ]