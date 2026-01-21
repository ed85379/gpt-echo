# muse_profile.py
from datetime import datetime, timezone
from app.databases.mongo_connector import mongo

PROFILE_COLLECTION = "muse_profile"


class MuseProfile:
    def get_section(self, section):
        return mongo.get_collection(PROFILE_COLLECTION).find_one({"section": section})

    def get_sections(self, sections):
        """Return a list of section docs matching any of the given names."""
        return list(
            mongo.get_collection(PROFILE_COLLECTION)
            .find({"section": {"$in": sections}})
        )

    def get_pollable(self):
        """Return a list of section docs set pollable: true."""
        return list(
            mongo.find_documents(
                PROFILE_COLLECTION,
                {"pollable": True},
                projection={"section": 1, "content": 1, "_id": 0},
            )
        )

    def get_sections_except(self, exceptions):
        """Return all section docs *not* in the exceptions list."""
        return list(
            mongo.get_collection(PROFILE_COLLECTION)
            .find({"section": {"$nin": exceptions}})
        )

    def set_section(self, section, content):
        mongo.get_collection(PROFILE_COLLECTION).update_one(
            {"section": section},
            {
                "$set": {
                    "content": content,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

    def get_sections_by_category(self, category):
        """Return all section docs in the given category."""
        return list(
            mongo.get_collection(PROFILE_COLLECTION)
            .find({"category": category})
        )

    def get_sections_in_category(self, category, sections=None):
        """Return section docs in category, optionally filtering by section names."""
        query = {"category": category}
        if sections:
            query["section"] = {"$in": sections}
        return list(
            mongo.get_collection(PROFILE_COLLECTION)
            .find(query)
        )

    def get_sections_exclude_category(self, category):
        """Return all docs *not* in the given category."""
        return list(
            mongo.get_collection(PROFILE_COLLECTION)
            .find({"category": {"$ne": category}})
        )

    def get_sections_exclude(self, categories=None, sections=None):
        """Return all docs not in given categories or section names."""
        query = {}
        if categories:
            query["category"] = {"$nin": categories}
        if sections:
            query["section"] = {"$nin": sections}
        return list(
            mongo.get_collection(PROFILE_COLLECTION)
            .find(query)
        )

    def all_sections(self):
        return list(mongo.get_collection(PROFILE_COLLECTION).find({}))

muse_profile = MuseProfile()