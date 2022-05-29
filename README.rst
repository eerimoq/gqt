GraphQL tool
============

- Save latest query and cursor position.
- Print built query.
- Contols:
  - Execute built query when pressing <Enter>.
  - Toggle checkbox with <Space>.
  - Use arrows ro navigate.
  - Use '/' to fuzzy find field.
- Query is all selected visible leaves.
- Variables?

$ gql https://mys-lang.org/graphql
> activities
 standard_library
  ◻ number_of_downloads
  ☑ number_of_packages
   package
    ☑ name*: "foo"
    ◻ builds
    ◻ coverage
     latest_release
      ◻ description
      ☑ version
    ◻ name
    ️◻ number_of_downloads
  > packages
> statistics
<Enter>
$ gql https://mys-lang.org/graphql
{
  "data": {
    "standard_library": {
      "package": {
        "latest_release": {
          "version": "0.1.0"
        }
      }
    }
  }
}
