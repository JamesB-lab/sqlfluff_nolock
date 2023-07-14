"""A custom rule to check for NOLOCK implemented through the plugin system.

This uses the rules API supported from 2.0.0 onwards.
"""

import os.path
from typing import Tuple, List, Type

from sqlfluff.core.plugin import hookimpl
from sqlfluff.core.config import ConfigLoader
from sqlfluff.core.rules import (
    BaseRule,
    LintFix,
    LintResult,
    RuleContext,
)
from sqlfluff.core.rules.crawlers import SegmentSeekerCrawler
from sqlfluff.utils.functional import (
    FunctionalContext,
    sp,
)
from sqlfluff.core.parser import (
    BaseSegment,
    WhitespaceSegment,
    KeywordSegment,
)
from sqlfluff.core.parser.segments import (
    BracketedSegment,
    SymbolSegment,
)
from sqlfluff.dialects.dialect_tsql import (
    PostTableExpressionGrammar,
    TableHintSegment,
)

@hookimpl
def get_rules() -> List[Type[BaseRule]]:
    """Get plugin rules."""
    return [Rule_NOLOCK_L001]


@hookimpl
def load_default_config() -> dict:
    """Loads the default configuration for the plugin."""
    return ConfigLoader.get_global().load_config_file(
        file_dir=os.path.dirname(__file__),
        file_name="plugin_default_config.cfg",
    )


@hookimpl
def get_configs_info() -> dict:
    """Get rule config validations and descriptions."""
    return {
        "check_from": {"definition": "Flag to check FROM clauses"},
        "check_join": {"definition": "Flag to check JOIN clauses"},
    }


# These two decorators allow plugins
# to be displayed in the sqlfluff docs
class Rule_NOLOCK_L001(BaseRule):
    """Locking tables is forbidden

    Reference: https://learn.microsoft.com/en-us/sql/t-sql/queries/hints-transact-sql-table?view=sql-server-ver16

    **Anti-pattern**

    Not using `WITH (NOLOCK)` when accessing a table

    .. code-block:: sql

        SELECT mytable.mycol
        FROM mytable
        LEFT JOIN othertable ON mytable.id = othertable.id
        ORDER BY mytable.mycol;

    **Best practice**

    Ensure the table isn't locked.

    .. code-block:: sql

        SELECT mytable.mycol
        FROM mytable WITH (NOLOCK)
        LEFT JOIN othertable WITH (NOLOCK) ON mytable.id = othertable.id
        ORDER BY mytable.mycol;
    """

    groups = ("all",)
    config_keywords = []
    crawl_behaviour = SegmentSeekerCrawler({"from_expression_element"})
    is_fix_compatible = True

    def __init__(self, *args, **kwargs):
        """Overwrite __init__ to set config."""
        super().__init__(*args, **kwargs)
        self.is_fixed = False

    def _eval(self, context: RuleContext):
        """We should not lock the table when selecting."""
        assert context.segment.is_type("from_expression_element")
        if self._lint(context):
            return None
        fixes = self._fixes(context)
        return LintResult(
            anchor = context.segment,
            description = "Missing table hint NOLOCK",
            fixes = fixes
        )

    def _lint(self, context: RuleContext) -> bool:
        fc = FunctionalContext(context)
        if not fc.segment.children(sp.is_type("table_expression")).children().any(sp.is_type("table_reference")):
            return True
        return fc.segment \
                .children(sp.is_type("post_table_expression")) \
                .children(sp.is_type('bracketed')) \
                .children(sp.is_type('query_hint_segment')) \
                .children(sp.is_type('keyword')) \
                .any(sp.raw_is('NOLOCK'))
    
    def _fixes(self, context: RuleContext)->Tuple[Type[LintFix]] | None:
        root_segment = FunctionalContext(context).segment
        # First check if a query_hint_segment already exists, if so don't provide a fix
        query_hint_segment = root_segment.children(sp.is_type("post_table_expression")) \
            .children(sp.is_type('bracketed')) \
            .children(sp.is_type('query_hint_segment'))
        if len(query_hint_segment) > 0:
            return None
        # Otherwise find an appropriate anchor and create the segment after it
        alias_expression_segment = root_segment.children(sp.is_type('alias_expression'))
        table_expression_segment = root_segment.children(sp.is_type('table_expression'))
        create_after_anchor: BaseSegment
        if len(alias_expression_segment) > 0:
            create_after_anchor = alias_expression_segment[0]
        elif len(table_expression_segment) > 0:
            create_after_anchor = table_expression_segment[0]
        else:
            return None
        start = SymbolSegment('(', type = 'start_bracket')
        end = SymbolSegment(')', type = 'end_bracket')
        return [
            LintFix.create_after(
                anchor_segment = create_after_anchor,
                edit_segments = [
                    WhitespaceSegment(),
                    PostTableExpressionGrammar(
                        [
                            KeywordSegment('WITH'),
                            WhitespaceSegment(),
                            BracketedSegment(
                                [
                                    TableHintSegment(
                                        [
                                            start,
                                            KeywordSegment('NOLOCK'),
                                            end,
                                        ],
                                    ),
                                ],
                                start_bracket = [start],
                                end_bracket = [end],
                            ),
                        ],
                    ),
                ],
            )
        ]
