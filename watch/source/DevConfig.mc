import Toybox.Lang;

//! DEV / SIDELOAD ONLY — compile-time overrides for values that normally come
//! from app settings.
//!
//! Two situations need this:
//!   * the simulator wipes Application.Storage between runs, so pairing doesn't
//!     stick;
//!   * a sideloaded app gets no settings screen at all in Garmin Connect
//!     (Garmin serves settings metadata from the store), so there is nowhere to
//!     type a pairing code.
//!
//! Leave DEVICE_TOKEN / CAR_LABEL "" and FAKE_FLAGS false for real builds.
//! After changing them, run:
//!     git update-index --skip-worktree watch/source/DevConfig.mc
//! so your token never gets committed. (`--no-skip-worktree` to undo.)
(:glance)
module DevConfig {
    //! A device token from `POST /v1/pair`. Skips pairing entirely.
    const DEVICE_TOKEN = "";

    //! Overrides the "Car name" setting when set.
    const CAR_LABEL = "";

    //! Forces every advisory icon (service / washer / tyre) on so the icon row
    //! can be eyeballed without waiting for the car to actually report a
    //! warning. MUST be false for any real / release build.
    const FAKE_FLAGS = false;
}
