#![cfg(windows)]

use std::ffi::c_void;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::OnceLock;

use windows::core::{implement, w, Error, GUID, HRESULT, IUnknown, Interface, PCWSTR, PSTR, Result};
use windows::Win32::Foundation::{
    BOOL, CLASS_E_CLASSNOTAVAILABLE, CLASS_E_NOAGGREGATION, E_FAIL, E_POINTER,
    ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND, HINSTANCE, HMODULE, MAX_PATH, S_FALSE, S_OK,
    TRUE,
};
use windows::Win32::System::Com::{IDataObject, IClassFactory, IClassFactory_Impl};
use windows::Win32::System::LibraryLoader::GetModuleFileNameW;
use windows::Win32::System::Registry::{
    RegCreateKeyW, RegDeleteTreeW, RegSetValueExW, HKEY, HKEY_CURRENT_USER, REG_SZ,
};
use windows::Win32::System::SystemServices::DLL_PROCESS_ATTACH;
use windows::Win32::UI::Shell::Common::ITEMIDLIST;
use windows::Win32::UI::Shell::{
    CMINVOKECOMMANDINFO, CMF_DEFAULTONLY, IContextMenu, IContextMenu_Impl, IShellExtInit,
    IShellExtInit_Impl,
};
use windows::Win32::UI::WindowsAndMessaging::{
    AppendMenuW, CreatePopupMenu, MessageBoxW, HMENU, MB_OK, MF_BYPOSITION, MF_POPUP, MF_STRING,
};

const SHELL_EXTENSION_CLSID: GUID = GUID::from_u128(0x8c5d7c56_65d0_4f31_a8aa_3101a0f1fd41);
const SHELL_EXTENSION_CLSID_TEXT: &str = "{8C5D7C56-65D0-4F31-A8AA-3101A0F1FD41}";
const HANDLER_NAME: &str = "PContext";
const SUBMENU_TITLE: PCWSTR = w!("PContext");
const TEST_COMMAND_TITLE: PCWSTR = w!("Native test");
const TEST_MESSAGE_TEXT: PCWSTR = w!("PContext native shell extension loaded successfully.");
const TEST_MESSAGE_TITLE: PCWSTR = w!("PContext");

static MODULE_HANDLE: OnceLock<usize> = OnceLock::new();
static DLL_OBJECT_COUNT: AtomicU32 = AtomicU32::new(0);
static DLL_LOCK_COUNT: AtomicU32 = AtomicU32::new(0);

#[implement(IShellExtInit, IContextMenu)]
struct PContextShellExtension;

impl PContextShellExtension {
    fn new() -> Self {
        DLL_OBJECT_COUNT.fetch_add(1, Ordering::SeqCst);
        Self
    }
}

impl Drop for PContextShellExtension {
    fn drop(&mut self) {
        DLL_OBJECT_COUNT.fetch_sub(1, Ordering::SeqCst);
    }
}

impl IShellExtInit_Impl for PContextShellExtension_Impl {
    fn Initialize(
        &self,
        _pidlfolder: *const ITEMIDLIST,
        _data_object: Option<&IDataObject>,
        _program_id_key: HKEY,
    ) -> Result<()> {
        Ok(())
    }
}

impl IContextMenu_Impl for PContextShellExtension_Impl {
    fn QueryContextMenu(
        &self,
        menu: HMENU,
        _index_menu: u32,
        id_cmd_first: u32,
        _id_cmd_last: u32,
        flags: u32,
    ) -> Result<()> {
        if (flags & CMF_DEFAULTONLY) != 0 {
            return Ok(());
        }

        unsafe {
            let submenu = CreatePopupMenu()?;

            AppendMenuW(
                submenu,
                MF_STRING,
                id_cmd_first as usize,
                TEST_COMMAND_TITLE,
            )?;

            AppendMenuW(
                menu,
                MF_BYPOSITION | MF_POPUP,
                submenu.0 as usize,
                SUBMENU_TITLE,
            )?;
        }

        Ok(())
    }

    fn InvokeCommand(&self, command_info: *const CMINVOKECOMMANDINFO) -> Result<()> {
        let command_info = unsafe { command_info.as_ref() }.ok_or_else(|| Error::from(E_POINTER))?;

        let verb_value = command_info.lpVerb.0 as usize;
        if (verb_value >> 16) != 0 {
            return Ok(());
        }

        let command_offset = (verb_value & 0xFFFF) as u32;

        if command_offset == 0 {
            unsafe {
                MessageBoxW(
                    command_info.hwnd,
                    TEST_MESSAGE_TEXT,
                    TEST_MESSAGE_TITLE,
                    MB_OK,
                );
            }
        }

        Ok(())
    }

    fn GetCommandString(
        &self,
        _id_cmd: usize,
        _flags: u32,
        _reserved: *const u32,
        _command_string: PSTR,
        _cch_max: u32,
    ) -> Result<()> {
        Ok(())
    }
}

#[implement(IClassFactory)]
struct PContextClassFactory;

impl PContextClassFactory {
    fn new() -> Self {
        DLL_OBJECT_COUNT.fetch_add(1, Ordering::SeqCst);
        Self
    }
}

impl Drop for PContextClassFactory {
    fn drop(&mut self) {
        DLL_OBJECT_COUNT.fetch_sub(1, Ordering::SeqCst);
    }
}

impl IClassFactory_Impl for PContextClassFactory_Impl {
    fn CreateInstance(
        &self,
        outer: Option<&IUnknown>,
        interface_id: *const GUID,
        result_object: *mut *mut c_void,
    ) -> Result<()> {
        if result_object.is_null() {
            return Err(Error::from(E_POINTER));
        }

        unsafe {
            *result_object = std::ptr::null_mut();
        }

        if outer.is_some() {
            return Err(Error::from(CLASS_E_NOAGGREGATION));
        }

        let unknown: IUnknown = PContextShellExtension::new().into();

        unsafe {
            unknown.query(interface_id, result_object).ok()?;
        }

        Ok(())
    }

    fn LockServer(&self, lock: BOOL) -> Result<()> {
        if lock.as_bool() {
            DLL_LOCK_COUNT.fetch_add(1, Ordering::SeqCst);
        } else {
            DLL_LOCK_COUNT.fetch_sub(1, Ordering::SeqCst);
        }

        Ok(())
    }
}

#[no_mangle]
pub extern "system" fn DllMain(
    module: HINSTANCE,
    reason: u32,
    _reserved: *mut c_void,
) -> BOOL {
    if reason == DLL_PROCESS_ATTACH {
        let _ = MODULE_HANDLE.set(module.0 as usize);
    }

    TRUE
}

#[no_mangle]
pub extern "system" fn DllCanUnloadNow() -> HRESULT {
    if DLL_OBJECT_COUNT.load(Ordering::SeqCst) == 0
        && DLL_LOCK_COUNT.load(Ordering::SeqCst) == 0
    {
        S_OK
    } else {
        S_FALSE
    }
}

#[no_mangle]
pub extern "system" fn DllGetClassObject(
    class_id: *const GUID,
    interface_id: *const GUID,
    result_object: *mut *mut c_void,
) -> HRESULT {
    let result = (|| -> Result<()> {
        if result_object.is_null() {
            return Err(Error::from(E_POINTER));
        }

        unsafe {
            *result_object = std::ptr::null_mut();
        }

        let class_id = unsafe { class_id.as_ref() }.ok_or_else(|| Error::from(E_POINTER))?;
        if *class_id != SHELL_EXTENSION_CLSID {
            return Err(Error::from(CLASS_E_CLASSNOTAVAILABLE));
        }

        let factory: IClassFactory = PContextClassFactory::new().into();

        unsafe {
            factory.query(interface_id, result_object).ok()?;
        }

        Ok(())
    })();

    match result {
        Ok(()) => S_OK,
        Err(error) => error.code(),
    }
}

#[no_mangle]
pub extern "system" fn DllRegisterServer() -> HRESULT {
    match register_shell_extension() {
        Ok(()) => S_OK,
        Err(error) => error.code(),
    }
}

#[no_mangle]
pub extern "system" fn DllUnregisterServer() -> HRESULT {
    match unregister_shell_extension() {
        Ok(()) => S_OK,
        Err(error) => error.code(),
    }
}

fn register_shell_extension() -> Result<()> {
    let dll_path = current_module_path()?;

    write_default_value(
        &format!(r"Software\Classes\CLSID\{}", SHELL_EXTENSION_CLSID_TEXT),
        HANDLER_NAME,
    )?;

    write_default_value(
        &format!(r"Software\Classes\CLSID\{}\InprocServer32", SHELL_EXTENSION_CLSID_TEXT),
        &dll_path,
    )?;

    write_named_value(
        &format!(r"Software\Classes\CLSID\{}\InprocServer32", SHELL_EXTENSION_CLSID_TEXT),
        "ThreadingModel",
        "Apartment",
    )?;

    write_default_value(
        r"Software\Classes\*\shellex\ContextMenuHandlers\PContext",
        SHELL_EXTENSION_CLSID_TEXT,
    )?;

    write_default_value(
        r"Software\Classes\Directory\shellex\ContextMenuHandlers\PContext",
        SHELL_EXTENSION_CLSID_TEXT,
    )?;
    write_default_value(
        r"Software\Classes\Folder\shellex\ContextMenuHandlers\PContext",
        SHELL_EXTENSION_CLSID_TEXT,
    )?;

    write_default_value(
        r"Software\Classes\Directory\Background\shellex\ContextMenuHandlers\PContext",
        SHELL_EXTENSION_CLSID_TEXT,
    )?;

    write_default_value(
        r"Software\Classes\Drive\shellex\ContextMenuHandlers\PContext",
        SHELL_EXTENSION_CLSID_TEXT,
    )?;

    write_named_value(
        r"Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved",
        SHELL_EXTENSION_CLSID_TEXT,
        HANDLER_NAME,
    )?;

    Ok(())
}

fn unregister_shell_extension() -> Result<()> {
    delete_tree(r"Software\Classes\*\shellex\ContextMenuHandlers\PContext")?;
    delete_tree(r"Software\Classes\Directory\shellex\ContextMenuHandlers\PContext")?;
    delete_tree(r"Software\Classes\Folder\shellex\ContextMenuHandlers\PContext")?;
    delete_tree(r"Software\Classes\Directory\Background\shellex\ContextMenuHandlers\PContext")?;
    delete_tree(r"Software\Classes\Drive\shellex\ContextMenuHandlers\PContext")?;
    delete_tree(&format!(r"Software\Classes\CLSID\{}", SHELL_EXTENSION_CLSID_TEXT))?;
    Ok(())
}

fn current_module_path() -> Result<String> {
    let module_raw = MODULE_HANDLE
        .get()
        .copied()
        .ok_or_else(|| Error::from(E_FAIL))?;

    let module = HMODULE(module_raw as *mut c_void);
    let mut buffer = vec![0u16; MAX_PATH as usize];

    loop {
        let length = unsafe { GetModuleFileNameW(module, &mut buffer) } as usize;

        if length == 0 {
            return Err(Error::from_win32());
        }

        if length < buffer.len() - 1 {
            return Ok(String::from_utf16_lossy(&buffer[..length]));
        }

        buffer.resize(buffer.len() * 2, 0);
    }
}

fn to_wide(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}

fn write_default_value(key_path: &str, value: &str) -> Result<()> {
    write_registry_value(key_path, None, value)
}

fn write_named_value(key_path: &str, value_name: &str, value: &str) -> Result<()> {
    write_registry_value(key_path, Some(value_name), value)
}

fn write_registry_value(
    key_path: &str,
    value_name: Option<&str>,
    value: &str,
) -> Result<()> {
    let key_path_wide = to_wide(key_path);
    let mut key = HKEY::default();

    unsafe {
        RegCreateKeyW(
            HKEY_CURRENT_USER,
            PCWSTR(key_path_wide.as_ptr()),
            &mut key,
        )
        .ok()?;
    }

    let value_wide = to_wide(value);
    let value_bytes = unsafe {
        std::slice::from_raw_parts(
            value_wide.as_ptr() as *const u8,
            value_wide.len() * std::mem::size_of::<u16>(),
        )
    };

    let value_name_wide = value_name.map(to_wide);

    unsafe {
        RegSetValueExW(
            key,
            value_name_wide
                .as_ref()
                .map(|item| PCWSTR(item.as_ptr()))
                .unwrap_or(PCWSTR::null()),
            0,
            REG_SZ,
            Some(value_bytes),
        )
        .ok()?;
    }

    Ok(())
}

fn delete_tree(key_path: &str) -> Result<()> {
    let key_path_wide = to_wide(key_path);

    let status = unsafe {
        RegDeleteTreeW(
            HKEY_CURRENT_USER,
            PCWSTR(key_path_wide.as_ptr()),
        )
    };

    if status == ERROR_FILE_NOT_FOUND || status == ERROR_PATH_NOT_FOUND {
        return Ok(());
    }

    status.ok()?;
    Ok(())
}