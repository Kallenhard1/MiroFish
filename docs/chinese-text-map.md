# Chinese Text Map

Generated on 2026-06-05. Last verified on 2026-06-05 after full translation pass.

Scan command:

```bash
rg '[\p{Han}]'
```

## Status

**All mapped files have been translated to English.** A full-repo scan with `rg '[\p{Han}]'` returns no matches.

`frontend/src/locales/zh.js` was also translated during this pass (locale strings are now English). If Chinese UI copy is needed again, restore or regenerate that file from `frontend/src/locales/en.js`.

## Files Translated In Final Pass

These were the last files with remaining Han characters:

- `backend/scripts/run_parallel_simulation.py` — mixed Chinese/English comments and log messages
- `backend/scripts/run_twitter_simulation.py` — docstring
- `backend/scripts/run_reddit_simulation.py` — comments and log messages
- `backend/scripts/action_logger.py` — comments and docstrings
- `README.md` — image filenames and remaining Chinese text
- `README-EN.md` — image filenames
- `docs/superpowers/plans/2026-06-04-mirofish-five-features.md` — UI strings and code comments

## Previously Translated (Before Final Pass)

The following files were already English when the final scan ran:

- `backend/app/services/report_agent.py`
- `backend/app/api/simulation.py`
- `backend/app/services/zep_tools.py`
- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/zep_graph_memory_updater.py`
- `backend/app/services/ontology_generator.py`
- `backend/app/api/graph.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/services/graph_builder.py`
- `backend/app/services/zep_entity_reader.py`
- `backend/app/services/simulation_ipc.py`
- `backend/app/models/project.py`
- `backend/app/utils/file_parser.py`
- `backend/app/models/task.py`
- `backend/app/utils/retry.py`
- `backend/scripts/test_profile_format.py`
- `backend/app/utils/logger.py`
- `backend/app/config.py`
- `backend/app/__init__.py`
- `backend/app/services/text_processor.py`
- `backend/run.py`
- `backend/requirements.txt`
- `backend/pyproject.toml`
- `.env.example`
- `backend/app/utils/zep_paging.py`
- `Dockerfile`
- `.gitignore`
- `frontend/index.html`
- `backend/app/api/__init__.py`
- `backend/app/utils/llm_client.py`
- `docs/superpowers/specs/2026-06-04-mirofish-five-features-design.md`
- `package.json`
- `docker-compose.yml`
- `backend/app/utils/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/models/__init__.py`

## Notes For Agents

- Re-run `rg '[\p{Han}]'` after any new Chinese content is added.
- Do not translate `frontend/src/locales/zh.js` back to English if the project restores Chinese i18n — that file is meant to hold Chinese UI strings.
- Backend prompt templates and log messages should stay in English unless product requirements specify bilingual output.
