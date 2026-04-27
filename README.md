# OpenAir

**Native Max For Live GUIs for AirWindows Plugins**

OpenAir is a repository dedicated to hosting native Max for Live (M4L) ports of the incredible [Airwindows](https://www.airwindows.com/) VST plugins. This project leverages custom-built Max externals to bring the bare-metal DSP of Airwindows directly into the Ableton Live and Max/MSP ecosystem.

## Installation

This repository is structured as a **Standard Max Package**. To install and use the plugins:

1. Download or clone this repository.
2. Move the entire `OpenAir` folder into your Max Packages directory:
   * **Windows**: `Documents\Max 8\Packages\`
   * **macOS**: `~/Documents/Max 8/Packages/`
3. Restart Ableton Live or Max. The externals and `.amxd` plugins will automatically be indexed and available for use.

## Repository Structure

* `externals/`: Contains the compiled C++ DSP objects (`.mxe64` for Windows, `.mxo` for macOS).
* `patchers/`: Houses the actual Max for Live Devices (`.amxd`) and any utility patches (`.maxpat`).
* `docs/`: Contains interactive help files (`.maxhelp`) and XML reference documentation (`.maxref.xml`).
* `media/`: Stores images, icons, and audio assets used by the plugin GUIs.

## Contributing to Documentation

To make this repository highly durable and user-friendly, we aim to provide standard Max documentation for every ported external. 

### 1. Creating Help Files (`.maxhelp`)
A Max help file is the interactive patch that opens when a user Alt+Clicks (Option+Clicks) on an object.
* Open Max and create a new patch demonstrating the basic usage of the external.
* Add comments explaining the inputs, outputs, and parameters.
* Save the patch into the `docs/` folder.
* **Naming Convention**: It must exactly match the external name with the `.maxhelp` extension. For example, if the external is `airfx.totape7~`, the help file must be named `airfx.totape7~.maxhelp`.

### 2. Creating Reference Files (`.maxref.xml`)
Reference files populate the Max reference sidebar and provide detailed documentation for object attributes and messages.
* You can generate a basic XML template in Max by right-clicking an object and selecting **Open Reference**, then clicking the edit button.
* Fill in the digest, description, and list out the parameters (attributes).
* Save the generated XML into the `docs/` folder.
* **Naming Convention**: Similar to help files, use `airfx.plugin_name~.maxref.xml` (e.g., `airfx.totape7~.maxref.xml`).

---

*Authored by Dave Suona Bene*
