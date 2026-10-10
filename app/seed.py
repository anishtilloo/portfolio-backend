"""Starter content so the blog isn't empty on first run.

These are first drafts on topics Anish has worked through. Edit or delete them
from the writing desk (/admin) once the site is running.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Link, Post
from app.text import reading_minutes

TITLE_RACE = """\
A detail page I was working on sets the browser tab title to the record it is
showing. Every so often the tab named one record while the page showed another.
Refreshing fixed it, which is usually a sign of a race.

## What was happening

The page fetched its data in `onMounted` and set the title when the request came back:

```ts
onMounted(async () => {
  const order = await fetchOrder(route.params.id)
  document.title = `Order ${order.reference}`
})
```

Two things go wrong with this.

1. Vue Router reuses the component when only the route param changes, so
   `onMounted` does not run again and the title stays on the first record.
2. Once you fix that by watching the param, two requests can be in flight at the
   same time. If the older one is slower, it finishes last and writes the old
   title over the new one.

## The fix

Treat the title as something derived from state, and make sure a stale response
can never write state in the first place.

```ts
const order = ref<Order | null>(null)

watch(
  () => route.params.id,
  async (id, _old, onCleanup) => {
    let stale = false
    onCleanup(() => (stale = true))

    order.value = null
    const result = await fetchOrder(id as string)
    if (!stale) order.value = result
  },
  { immediate: true },
)

watchEffect(() => {
  document.title = order.value ? `Order ${order.value.reference}` : 'Loading order'
})
```

`onCleanup` runs just before the watcher fires again, so the previous request
marks itself stale and its result is dropped. The title is set in exactly one
place and can only ever reflect what is on screen.

## What I took from it

- `document.title` is a side effect. Keep it in one `watchEffect`, not scattered
  through data-loading code.
- Any `await` inside a watcher needs an answer to "what if this fires again
  before I finish?"
- If you can cancel the request (an `AbortController` works well here), do that
  in `onCleanup` as well, so the browser stops doing work nobody wants.
"""

ARRAY_PARAMS = """\
I have been moving a set of analytics functions from taking a single id, such
as `p_account_id integer`, to taking a list of them. Calling a function once per
id and adding the results up in the API works for counts, and breaks for
anything that is not additive, like averages or distinct counts. The function
itself has to accept the list.

## Scalar to array

The signature changes from `integer` to `integer[]`, and the filter changes from
`=` to `= ANY(...)`:

```sql
CREATE OR REPLACE FUNCTION weekly_event_counts(
    p_account_ids integer[],
    p_from       timestamptz,
    p_to         timestamptz
)
RETURNS TABLE (week_start date, events bigint)
LANGUAGE sql STABLE AS $$
    SELECT date_trunc('week', e.created_at AT TIME ZONE 'Pacific/Auckland')::date,
           count(*)
    FROM   events e
    WHERE  e.created_at >= p_from
    AND    e.created_at <  p_to
    AND    (p_account_ids IS NULL OR e.account_id = ANY (p_account_ids))
    GROUP  BY 1
    ORDER  BY 1;
$$;
```

`= ANY (array)` can still use an ordinary b-tree index on `account_id`, so the
plan stays the same shape as the scalar version.

## Things that caught me out

**Decide what "no filter" means.** I use `NULL` for "all accounts". An empty
array `'{}'` matches nothing, which is the correct reading of "none of them" but
is rarely what a caller sending an empty selection wants. Pick one rule and
write it down in the function comment.

**You cannot change a parameter's type in place.** `CREATE OR REPLACE` with a
different argument type creates a second, overloaded function. Drop the old
signature explicitly, or callers that pass an untyped literal will hit an
"is not unique" error.

```sql
DROP FUNCTION IF EXISTS weekly_event_counts(integer, timestamptz, timestamptz);
```

**Bucket weeks in the customer's time zone.** `date_trunc('week', created_at)`
uses the session time zone. Converting with `AT TIME ZONE` first puts an event
from Monday morning in Auckland into Monday's week, not the week before.

**Pass a real array from the driver.** Most Postgres drivers map a native list
to an array parameter. Building a comma-separated string and splitting it in SQL
gives up type checking for no benefit.
"""

NEST_BREAKPOINTS = """\
Breakpoints in a NestJS service showed as grey hollow circles ("unbound") in
VS Code, and after every file save the debugger dropped off entirely.

Two separate causes:

**No source maps.** The debugger runs the compiled JavaScript in `dist/` and
needs maps to find the matching TypeScript line. In `tsconfig.json`:

```json
{ "compilerOptions": { "sourceMap": true } }
```

**Watch mode restarts the process.** `nest start --debug --watch` kills and
restarts Node on every change, so an attached debugger loses its target. Tell
VS Code to reattach:

```json
{
  "type": "node",
  "request": "attach",
  "name": "Attach to Nest",
  "port": 9229,
  "restart": true,
  "sourceMaps": true,
  "outFiles": ["${workspaceFolder}/dist/**/*.js"]
}
```

With `restart: true` the debugger reconnects each time the process comes back,
and breakpoints bind again without touching anything.
"""

SKILLS_NOTE = """\
A skill is a folder with a `SKILL.md` in it: instructions an AI coding agent
loads when a task matches the skill's description. That is the whole idea, and
it is why two habits matter more than which skills you install.

**Read the prompt before you install it.** A skill runs with whatever access
your agent has: your files, your shell, your credentials. Its instructions are
plain text, so reading them takes a couple of minutes. Treat an unread skill
like an unread shell script.

**Put standing instructions in the project, not in each prompt.** Anything you
find yourself repeating ("use pnpm", "tests live next to the file") belongs in
`CLAUDE.md` or `AGENTS.md`, where it is applied every time and reviewed like any
other file in the repository.
"""

POSTS = [
    {
        "kind": "article",
        "title": "A stale tab title in Vue 3, and the race behind it",
        "slug": "vue-3-stale-document-title",
        "summary": (
            "The tab named one record while the page showed another. The cause was an "
            "async race, and the fix is to treat the title as derived state."
        ),
        "body_md": TITLE_RACE,
        "tags": ["vue", "typescript", "debugging"],
        "days_ago": 4,
    },
    {
        "kind": "article",
        "title": "Moving PostgreSQL function parameters from one id to an array",
        "slug": "postgres-function-array-parameters",
        "summary": (
            "What changes when an analytics function has to filter by many ids, and "
            "the four details that caught me out along the way."
        ),
        "body_md": ARRAY_PARAMS,
        "tags": ["postgresql", "sql"],
        "days_ago": 18,
    },
    {
        "kind": "note",
        "title": "NestJS breakpoints that will not bind in VS Code",
        "slug": "nestjs-breakpoints-vs-code",
        "summary": "Turn on source maps, and let the debugger reattach when watch mode restarts.",
        "body_md": NEST_BREAKPOINTS,
        "tags": ["nestjs", "debugging"],
        "days_ago": 31,
    },
    {
        "kind": "note",
        "title": "Two habits for working with AI skills",
        "slug": "two-habits-for-ai-skills",
        "summary": (
            "Read a skill's prompt before installing it, and keep standing "
            "instructions in the repo."
        ),
        "body_md": SKILLS_NOTE,
        "tags": ["ai", "tooling"],
        "days_ago": 45,
    },
]

LINKS = [
    {
        "url": "https://vuejs.org/guide/essentials/watchers.html",
        "title": "Watchers",
        "source": "Vue.js docs",
        "takeaway": (
            "The section on side-effect cleanup is the part to reread: it shows how to "
            "cancel or ignore a stale async call when a watcher fires again."
        ),
        "tags": ["vue"],
        "days_ago": 5,
    },
    {
        "url": "https://www.postgresql.org/docs/current/arrays.html",
        "title": "Arrays",
        "source": "PostgreSQL docs",
        "takeaway": (
            "Covers array literals, ANY and ALL comparisons, and the difference between "
            "an empty array and NULL, which matters for function parameters."
        ),
        "tags": ["postgresql"],
        "days_ago": 19,
    },
    {
        "url": "https://modelcontextprotocol.io/",
        "title": "Model Context Protocol",
        "source": "modelcontextprotocol.io",
        "takeaway": (
            "The reference for how tools, resources and prompts are exposed to an AI "
            "client. Useful background before wrapping an internal API as MCP tools."
        ),
        "tags": ["ai", "mcp"],
        "days_ago": 27,
    },
]


async def seed(session: AsyncSession) -> dict[str, int]:
    """Insert starter posts and links into empty tables. Safe to run twice."""
    now = datetime.now(UTC)
    added = {"posts": 0, "links": 0}

    if not await session.scalar(select(func.count()).select_from(Post)):
        for item in POSTS:
            when = now - timedelta(days=item["days_ago"])
            session.add(
                Post(
                    kind=item["kind"],
                    title=item["title"],
                    slug=item["slug"],
                    summary=item["summary"],
                    body_md=item["body_md"],
                    tags=item["tags"],
                    reading_minutes=reading_minutes(item["body_md"]),
                    published=True,
                    published_at=when,
                    created_at=when,
                    updated_at=when,
                )
            )
        added["posts"] = len(POSTS)

    if not await session.scalar(select(func.count()).select_from(Link)):
        for item in LINKS:
            session.add(
                Link(
                    url=item["url"],
                    title=item["title"],
                    source=item["source"],
                    takeaway=item["takeaway"],
                    tags=item["tags"],
                    created_at=now - timedelta(days=item["days_ago"]),
                )
            )
        added["links"] = len(LINKS)

    await session.commit()
    return added
