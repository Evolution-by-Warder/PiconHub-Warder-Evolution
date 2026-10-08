from __future__ import annotations

import hashlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import auxiliary_catalog as catalog


CHECKPOINT = "8bf726a3d7ba046f5bc531c8236b573963b7557a"
SOURCE_SHA = "1" * 64
PROVENANCE = "qc=13dd00b5624c4b6659574cdddedd503edc18947c; visual-approval=fixture"
PNG_SIZE = (220, 132)


def png_bytes(size=PNG_SIZE, color=(30, 60, 90, 255)):
    stream = io.BytesIO()
    Image.new("RGBA", size, color).save(stream, format="PNG")
    return stream.getvalue()


def record(kind="provider-logo", filename="ACME TV.png", black=None, white=None):
    return {
        "identity": f"{kind}::{filename}",
        "kind": kind,
        "filename": filename,
        "black_sha256": hashlib.sha256(black or png_bytes()).hexdigest(),
        "white_sha256": hashlib.sha256(white or png_bytes(color=(240, 240, 240, 255))).hexdigest(),
        "transparent_source_sha256": SOURCE_SHA,
        "qc_status": "PASS",
        "visual_approval_provenance": PROVENANCE,
    }


class AuxiliaryCatalogTests(unittest.TestCase):
    def make_catalog(self, kind="provider-logo", filename="ACME TV.png", *, black=None, white=None):
        black = black or png_bytes()
        white = white or png_bytes(color=(240, 240, 240, 255))
        manifest = catalog.build_manifest(
            [record(kind, filename, black, white)],
            approved_candidate_checkpoint=CHECKPOINT,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for variant, data in (("black", black), ("white", white)):
                path = root / catalog._expected_asset_path(kind, variant, filename)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            validated = catalog.validate_manifest(manifest, root)
            yield root, manifest, validated

    def test_valid_provider_identity(self):
        for _, manifest, validated in self.make_catalog():
            self.assertEqual(manifest["entries"][0]["identity"], "provider-logo::ACME TV.png")
            self.assertEqual(
                catalog.lookup_auxiliary(validated, "provider-logo", "ACME TV.png", "black"),
                "auxiliary/provider-logo/black/ACME TV.png",
            )

    def test_valid_satellite_identity_has_no_orbital_mapping(self):
        for _, manifest, validated in self.make_catalog("satellite-logo", "150W.png"):
            entry = manifest["entries"][0]
            self.assertEqual(entry["identity"], "satellite-logo::150W.png")
            self.assertNotIn("orbital_position", entry)
            self.assertEqual(
                catalog.lookup_auxiliary(validated, "satellite-logo", "150W.png", "white"),
                "auxiliary/satellite-logo/white/150W.png",
            )
            self.assertFalse(hasattr(validated, "orbital_position"))

    def test_duplicate_identity_rejected(self):
        one = record()
        with self.assertRaises(catalog.AuxiliaryCatalogError):
            catalog.build_manifest([one, one], approved_candidate_checkpoint=CHECKPOINT)

    def test_duplicate_target_path_rejected(self):
        manifest = catalog.build_manifest(
            [record(), record("satellite-logo", "OTHER.png")],
            approved_candidate_checkpoint=CHECKPOINT,
        )
        manifest["entries"][1]["black"]["path"] = manifest["entries"][0]["black"]["path"]
        with self.assertRaisesRegex(catalog.AuxiliaryCatalogError, "duplicate asset path"):
            catalog._validate_manifest_shape(manifest)

    def test_bad_sha_rejected(self):
        black, white = png_bytes(), png_bytes(color=(240, 240, 240, 255))
        for _, manifest, _ in self.make_catalog(black=black, white=white):
            manifest["entries"][0]["black"]["sha256"] = "0" * 64
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for variant, data in (("black", black), ("white", white)):
                    path = root / catalog._expected_asset_path("provider-logo", variant, "ACME TV.png")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                with self.assertRaises(catalog.AuxiliaryCatalogError):
                    catalog.validate_manifest(manifest, root)

    def test_missing_black_or_white_rejected(self):
        manifest = catalog.build_manifest([record()], approved_candidate_checkpoint=CHECKPOINT)
        del manifest["entries"][0]["white"]
        with self.assertRaises(catalog.AuxiliaryCatalogError):
            catalog._validate_manifest_shape(manifest)

    def test_invalid_dimensions_rejected(self):
        black, white = png_bytes((219, 132)), png_bytes(color=(240, 240, 240, 255))
        manifest = catalog.build_manifest(
            [record(black=black, white=white)], approved_candidate_checkpoint=CHECKPOINT
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for variant, data in (("black", black), ("white", white)):
                path = root / catalog._expected_asset_path("provider-logo", variant, "ACME TV.png")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            with self.assertRaisesRegex(catalog.AuxiliaryCatalogError, "220"):
                catalog.validate_manifest(manifest, root)

    def test_invalid_filename_and_path_traversal_rejected(self):
        for name in ("../x.png", "folder/x.png", r"..\\x.png", "bad\x00.png"):
            with self.subTest(name=name), self.assertRaises(catalog.AuxiliaryCatalogError):
                catalog.build_manifest([record(filename=name)], approved_candidate_checkpoint=CHECKPOINT)
        manifest = catalog.build_manifest([record()], approved_candidate_checkpoint=CHECKPOINT)
        manifest["entries"][0]["black"]["path"] = "auxiliary/provider-logo/black/../../x.png"
        with self.assertRaises(catalog.AuxiliaryCatalogError):
            catalog._validate_manifest_shape(manifest)

    def test_channel_namespace_collision_rejected(self):
        manifest = catalog.build_manifest([record()], approved_candidate_checkpoint=CHECKPOINT)
        manifest["entries"][0]["black"]["path"] = "picons/13.0e/provider/black/ACME TV.png"
        with self.assertRaises(catalog.AuxiliaryCatalogError):
            catalog._validate_manifest_shape(manifest)

    def test_unknown_lookup_is_clean_miss(self):
        for _, _, validated in self.make_catalog():
            self.assertIsNone(catalog.lookup_auxiliary(validated, "provider-logo", "MISSING.png", "black"))
            self.assertIsNone(catalog.lookup_auxiliary(validated, "provider-logo", "acme tv.png", "black"))

    def test_orphan_asset_rejected(self):
        black, white = png_bytes(), png_bytes(color=(240, 240, 240, 255))
        manifest = catalog.build_manifest([record(black=black, white=white)], approved_candidate_checkpoint=CHECKPOINT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for variant, data in (("black", black), ("white", white)):
                path = root / catalog._expected_asset_path("provider-logo", variant, "ACME TV.png")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            orphan = root / "auxiliary/provider-logo/black/orphan.png"
            orphan.write_bytes(png_bytes())
            with self.assertRaisesRegex(catalog.AuxiliaryCatalogError, "orphan"):
                catalog.validate_manifest(manifest, root)

    def test_channel_path_collision_rejected(self):
        black, white = png_bytes(), png_bytes(color=(240, 240, 240, 255))
        manifest = catalog.build_manifest([record(black=black, white=white)], approved_candidate_checkpoint=CHECKPOINT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for variant, data in (("black", black), ("white", white)):
                path = root / catalog._expected_asset_path("provider-logo", variant, "ACME TV.png")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            with self.assertRaisesRegex(catalog.AuxiliaryCatalogError, "collides"):
                catalog.validate_manifest(
                    manifest, root, channel_paths=("auxiliary/provider-logo/black/ACME TV.png",)
                )

    def test_archive_and_member_sha_pins(self):
        payload = png_bytes()
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("black/provider/ACME TV.png", payload)
        archive_bytes = archive_buffer.getvalue()
        member_sha = hashlib.sha256(payload).hexdigest()
        archive_sha = hashlib.sha256(archive_bytes).hexdigest()
        catalog.verify_pinned_archive(
            archive_bytes,
            expected_archive_sha256=archive_sha,
            expected_members={"black/provider/ACME TV.png": member_sha},
        )
        with self.assertRaisesRegex(catalog.AuxiliaryCatalogError, "archive SHA256"):
            catalog.verify_pinned_archive(
                archive_bytes, expected_archive_sha256="0" * 64,
                expected_members={"black/provider/ACME TV.png": member_sha},
            )
        with self.assertRaisesRegex(catalog.AuxiliaryCatalogError, "member SHA256"):
            catalog.verify_pinned_archive(
                archive_bytes, expected_archive_sha256=archive_sha,
                expected_members={"black/provider/ACME TV.png": "0" * 64},
            )

    def test_candidate_archive_bundle_is_bound_to_manifest(self):
        provider_black, provider_white = png_bytes(), png_bytes(color=(240, 240, 240, 255))
        satellite_black, satellite_white = png_bytes(color=(10, 10, 10, 255)), png_bytes(color=(250, 250, 250, 255))
        provider_source, satellite_source = png_bytes(color=(20, 30, 40, 100)), png_bytes(color=(60, 70, 80, 100))
        records = [
            record("provider-logo", "ACME.png", provider_black, provider_white),
            record("satellite-logo", "150W.png", satellite_black, satellite_white),
        ]
        records[0]["transparent_source_sha256"] = hashlib.sha256(provider_source).hexdigest()
        records[1]["transparent_source_sha256"] = hashlib.sha256(satellite_source).hexdigest()
        manifest = catalog.build_manifest(records, approved_candidate_checkpoint=CHECKPOINT)

        def zip_bytes(members):
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for member, data in members.items():
                    archive.writestr(member, data)
            return output.getvalue()

        archives = {
            "transparent-sources.zip": zip_bytes({
                "source-transparent/provider/ACME.png": provider_source,
                "source-transparent/satellite/150W.png": satellite_source,
            }),
            "provider-black-centered.zip": zip_bytes({"black/provider/ACME.png": provider_black}),
            "provider-white-centered.zip": zip_bytes({"white/provider/ACME.png": provider_white}),
            "satellite-black-white-centered.zip": zip_bytes({
                "black/satellite/150W.png": satellite_black,
                "white/satellite/150W.png": satellite_white,
            }),
        }
        pins = {name: hashlib.sha256(data).hexdigest() for name, data in archives.items()}
        catalog.verify_candidate_archives(manifest, archives, pins)
        bad_archives = dict(archives)
        bad_archives["provider-black-centered.zip"] = zip_bytes({"black/provider/OTHER.png": provider_black})
        bad_pins = dict(pins)
        bad_pins["provider-black-centered.zip"] = hashlib.sha256(
            bad_archives["provider-black-centered.zip"]
        ).hexdigest()
        with self.assertRaisesRegex(catalog.AuxiliaryCatalogError, "member set"):
            catalog.verify_candidate_archives(manifest, bad_archives, bad_pins)

    def test_manifest_order_and_serialization_are_deterministic(self):
        records = [record("provider-logo", "ZED.png"), record("provider-logo", "ACME.png")]
        a = catalog.build_manifest(records, approved_candidate_checkpoint=CHECKPOINT)
        b = catalog.build_manifest(list(reversed(records)), approved_candidate_checkpoint=CHECKPOINT)
        self.assertEqual(catalog.canonical_manifest_bytes(a), catalog.canonical_manifest_bytes(b))
        self.assertEqual([e["filename"] for e in a["entries"]], ["ACME.png", "ZED.png"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
