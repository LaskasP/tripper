from migrations.model_metadata import target_metadata


def test_migration_metadata_registers_auth_models_and_membership_account_fk() -> None:
    assert {"accounts", "sessions"} <= set(target_metadata.tables)

    membership = target_metadata.tables["trip_memberships"]
    foreign_key_targets = {
        foreign_key.target_fullname for foreign_key in membership.foreign_keys
    }

    assert "accounts.id" in foreign_key_targets
