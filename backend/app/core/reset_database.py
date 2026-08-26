from sqlalchemy import text

from .database import engine


def reset_database() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $$
                DECLARE
                    table_list TEXT;
                BEGIN
                    SELECT string_agg(
                        format('%I.%I', schemaname, tablename),
                        ', '
                    )
                    INTO table_list
                    FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename NOT IN ('alembic_version');

                    IF table_list IS NOT NULL THEN
                        EXECUTE 'TRUNCATE TABLE '
                            || table_list
                            || ' RESTART IDENTITY CASCADE';
                    END IF;
                END
                $$;
                """
            )
        )


if __name__ == "__main__":
    reset_database()
    print("Database data cleared successfully.")