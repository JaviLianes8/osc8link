# osc8link 1.0.0 author mutation table

The author mutation round of [CERT-1.0-REPORT.md](https://github.com/JaviLianes8/osc8link/blob/main/CERT-1.0-REPORT.md) (item 18).

56 mutants, each applied alone to a fresh clone of the pushed branch at e6eb2ce with every
fetched source and oracle present, the full suite run with `-x` and a 300 s per-test
limit. 53 killed at once; 3 survived and got contracts in 056f1d6, then were killed.

| Mutant | Killed by |
| --- | --- |
| M01 CAN no longer aborts | test_fuzz::test_the_library_reads_like_the_reference |
| M02 SUB no longer aborts | test_fuzz::test_the_library_reads_like_the_reference |
| M03 C1 9c to 9f no longer abort | test_docs::test_every_readme_example_runs_and_prints_its_comment |
| M04 CAN allowed between ESC and `]` | test_terminal_parser::test_cancel_before_the_bracket_breaks_the_opener |
| M05 DEL breaks the opener | test_oracle_xterm::test_every_printed_character_carries_the_terminals_link |
| M06 no leading zeros in the number | test_fuzz::test_the_library_reads_like_the_reference |
| M07 `8` at the end of the text not read | test_fuzz::test_the_library_reads_like_the_reference |
| M08 C1 ST not a terminator | test_docs::test_every_readme_example_runs_and_prints_its_comment |
| M09 BEL not a terminator | doctest of `osc8link` |
| M10 DEL kept in the payload | test_cli::test_list_escapes_controls_in_both_fields |
| M11 one semicolon is enough | test_fuzz::test_the_library_reads_like_the_reference |
| M12 the last semicolon splits | test_build::test_an_injected_sequence_in_the_url_stays_inside_the_target |
| M13 links without text yielded | test_fuzz::test_the_library_reads_like_the_reference |
| M14 an open link loses its tail | doctest of `iter_links` |
| M15 a close counts as a link | doctest of `contains_link` |
| M16 the last id wins | test_parse::test_the_first_id_wins_and_the_key_is_lowercase |
| M17 parameters without `=` kept | test_build::test_control_characters_in_the_url_cannot_end_the_sequence |
| M18 an empty id kept | test_build::test_control_characters_in_the_url_cannot_end_the_sequence |
| M19 `strip` keeps the opener's DEL | test_terminal_parser::test_an_opener_with_a_control_inside_is_read |
| M20 `strip` drops the opener's C0 | test_docs::test_every_guide_example_runs_and_prints_its_comment |
| M21 a cut-short tail is held back | survived; killed by test_stream::test_a_sequence_cut_short_inside_the_line_is_not_held_back |
| M22 an open tail is never held | test_cli::test_strip_streams_line_by_line_and_holds_an_open_sequence |
| M23 space kept in the URL | doctest of `encode_url` |
| M24 DEL kept in the URL | test_build::test_control_characters_in_the_url_cannot_end_the_sequence |
| M25 APC allowed in text | test_build::test_text_holding_a_control_string_is_rejected |
| M26 C1 APC allowed in text | test_build::test_text_holding_a_control_string_is_rejected |
| M27 empty URL accepted | test_auto_link::test_bad_input_fails_whatever_the_terminal |
| M28 `;` allowed in an id | doctest of `LinkError` |
| M29 DEL allowed in an id | test_build::test_an_id_outside_the_spec_alphabet_is_rejected |
| M30 an empty id written | test_build::test_an_empty_id_is_the_same_as_none |
| M31 terminators swapped | doctest of `osc8link` |
| M32 the encoded URL repeated in the fallback | test_auto_link::test_text_that_is_the_url_is_not_repeated |
| M33 `{url}` placeholder ignored | doctest of `auto_link` |
| M34 raw URL in the fallback | test_auto_link::test_a_pipe_gets_text_and_the_encoded_url |
| M35 plain `ValueError` for an empty URL | test_errors::test_bad_values_raise_link_error_with_a_short_message |
| M36 messages not cut | test_errors::test_bad_values_raise_link_error_with_a_short_message |
| M37 an empty `FORCE_HYPERLINK` forces | doctest of `auto_link` |
| M38 `FORCE_COLOR=false` ignored | test_detect::test_unknown_or_disabled_terminals_are_not |
| M39 `FORCE_COLOR` only exact `0` | test_detect_differences::test_force_color_reads_a_leading_zero_as_off |
| M40 an empty `WT_SESSION` ignored | test_detect::test_known_terminals_are_recognised |
| M41 iTerm2 3.1 rejected | test_detect::test_known_terminals_are_recognised |
| M42 VS Code 1.72 rejected | test_detect::test_known_terminals_are_recognised |
| M43 VTE 0.50.x rejected | test_detect::test_known_terminals_are_recognised |
| M44 VTE 5000 accepted | test_detect::test_unknown_or_disabled_terminals_are_not |
| M45 Unicode digits in packed versions | test_oracle_detect::test_recorded_answers_of_the_package |
| M46 U+00A0 not white space | test_oracle_detect::test_recorded_answers_of_the_package |
| M47 the sign ignored | test_detect::test_signs_and_long_zero_runs_read_like_parse_int |
| M48 foot not known | test_detect::test_known_terminals_are_recognised |
| M49 an `isatty` OSError escapes | test_detect::test_a_stream_whose_isatty_fails_is_not_a_terminal |
| M50 Unicode digits in a WezTerm Nix date | survived; killed by test_oracle_detect::test_recorded_answers_of_the_package |
| M51 backslash not escaped by `list` | test_cli::test_list_escapes_controls_in_both_fields |
| M52 `supports` exit codes swapped | test_cli::test_supports_reports_through_the_exit_code |
| M53 bad input exits 1 | test_cli::test_bad_input_exits_2_with_a_message |
| M54 `--bel` ignored | test_cli::test_link_text_defaults_to_the_url_and_bel_is_an_option |
| M55 EINVAL on a closed pipe raised | survived; killed by test_stream::test_a_reader_that_went_away_ends_the_command_quietly |
| M56 a tiny hold limit | test_fuzz::test_the_stream_filter_strips_like_strip_over_any_line_split |
