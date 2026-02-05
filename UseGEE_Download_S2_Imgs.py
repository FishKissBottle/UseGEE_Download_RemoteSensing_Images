import ee
import geemap
from datetime import datetime
import rasterio


def Process_Downloaded_Imgs(crsTransform: tuple, 
                            download_path: str):
    '''
    该函数用于去除边缘的空白部分，是下载影像之后进行的后处理
    crsTransform: 影像的仿射参数
    download_path: 影像下载的存储路径（这里是文件路径）
    ----------------------------------------------
    This function is used to remove the blank areas at the edges and is a post-processing step carried out after downloading the images
    crsTransform: Affine parameters of the image
    download_path: The savepath of downloaded images (file path)
    '''
    # 读取数据
    with rasterio.open(download_path) as src:
        download_data = src.read()
        
    download_data = download_data[:, 1:-1, 1:-1]

    trans = rasterio.transform.Affine(*crsTransform)
    prj = rasterio.crs.CRS.from_epsg(4326)

    _, height, width = download_data.shape

    profile = {
    'driver': 'GTiff',                 # 文件格式 // File format
    'dtype': download_data.dtype,      # 数据类型 // Data type
    'nodata': None,                    # 无数据值 (可选，这里假设没有) // No data value (Optional. Here, it is assumed that there is none.)
    'width': width,                    # 宽度 (列数) // Width
    'height': height,                  # 高度 (行数) // Height
    'count': download_data.shape[0],   # 波段数 // Bands num
    'crs': prj,                        # 坐标参考 // Coordinate reference
    'transform': trans,                # 仿射变换 // Affine transformation
    'compress': 'lzw',                 # 压缩方式 (可选) // Compression method (optional)
    }

    # 写入 ndarray_data，如果是多波段，一次性写入所有波段 // Write to ndarray_data. If it is a multi-band image, write all bands at once
    # write 方法期望数组的 shape 为 (bands, rows, cols) // The 'write' method expects the shape of the array to be (bands, rows, cols)
    with rasterio.open(download_path.replace('.tif', '.tif'), 'w', **profile) as dst:
        dst.write(download_data)



def Sentinel2_TOA_Download(lon_min: float, 
                           lon_max: float,
                           lat_min: float, 
                           lat_max: float,
                           start_date_str: str, 
                           end_date_str: str, 
                           download_folderpath: str,
                           bands=['B2', 'B3', 'B4', 'B8'],
                           coverage_ratio_threshold: float = 0.99,
                           resample_resolution: float = 0.00008983,
                           is_postprocess: bool = True
                           ):

    '''
    使用GEE下载Sentinel2_TOA数据
    lon_min: 影像的左边缘经度
    lon_max: 影像的右边缘经度
    lat_min: 影像的下边缘纬度值
    lat_max: 影像的上边缘纬度值
    start_date_str: 搜索时间范围的起点
    end_date_str: 搜索时间范围的终点
    download_folderpath: 用于存储影像的文件夹路径（这里是文件夹路径）
    bands: 需要下载的波段（默认['B2', 'B3', 'B4', 'B8']）
    coverage_ratio_threshold: 覆盖度的阈值（默认为0.99）
    resample_resolution: 重采样的目标分辨率（GEE下载的S2影像默认为0.00008983）
    is_postprocess: 是否进行后处理（默认进行）
    ------------------------------------------------------
    Download Sentinel2_TOA data using GEE
    lon_min: The longitude of the left edge of the image
    lon_max: The longitude of the right edge of the image
    lat_min: The latitude value of the lower edge of the image
    lat_max: The latitude value of the upper edge of the image
    start_date_str: The starting date of the search time range
    end_date_str: The endding date of the search time range
    download_folderpath: The folder path used for storing downloaded images (folder path)
    bands: The required bands（default ['B2', 'B3', 'B4', 'B8']）
    coverage_ratio_threshold: The threshold for coverage (default value is 0.99)
    resample_resolution: The target resolution for resampling (the default resolution for S2 images downloaded from GEE is 0.00008983)
    is_postprocess: Whether to perform post-processing (default is to do)
    '''

    # 定义一个矩形范围 参数传入格式(minLon, minLat, maxLon, maxLat) // Define a rectangular area  Parameter input format(minLon, minLat, maxLon, maxLat)
    rect_polygon = ee.Geometry.Rectangle(lon_min, lat_min, lon_max, lat_max)

    # TOA表观反射率: 获取COPERNICUS/S2_HARMONIZED数据集 // Get COPERNICUS/S2_HARMONIZED dataset
    # SR地表反射率： 获取COPERNICUS/S2_SR_HARMONIZED数据集 // Get COPERNICUS/S2_SR_HARMONIZED dataset
    sentinel2_toa_dataset = (ee.ImageCollection('COPERNICUS/S2_HARMONIZED').filterDate(start_date_str, end_date_str))

    # 输入筛选条件 // Input filtering criteria
    sentinel2_toa_dataset = sentinel2_toa_dataset.filterBounds(rect_polygon).select(bands).sort('system:time_start')

    # 获取搜索到的影像列表 // Get images list
    imgs_list = sentinel2_toa_dataset.toList(sentinel2_toa_dataset.size())
    imgs_num = sentinel2_toa_dataset.size().getInfo()

    print(f'>>> 共 {imgs_num} 景影像...')

    # 遍历每一景影像，当覆盖度达到阈值就进行下载 // Traverse each scene image. When the coverage reaches the threshold, start the download.
    for img_idx in range(imgs_num):
        # 读取第 img_idx 景影像 // Read the image with index img_idx from the GEE server
        selected_img = ee.Image(imgs_list.get(img_idx)).clip(rect_polygon)
        projection = selected_img.select('B2').projection()

        # 计算影像有效像素的个数（以B2波段为基准） // Calculate the number of effective pixels in the image (based on the B2 band)
        valid_pixels_num = selected_img.select('B2').reduceRegion(reducer=ee.Reducer.count(), geometry=rect_polygon, scale=10, maxPixels=1e13)
        valid_pixels_num = ee.Number(valid_pixels_num.get('B2'))

        # 计算影像总像素数量 // Calculate the total number of pixels in the image
        fullone_image = ee.Image(1).reproject(crs=projection.crs(), scale=10).clip(rect_polygon)
        total_pixels_num = fullone_image.reduceRegion(reducer=ee.Reducer.count(), geometry=rect_polygon, scale=10, maxPixels=1e13)
        total_pixels_num = ee.Number(total_pixels_num.get('constant'))

        # 有效像素数 / 总像素数 = 覆盖率 // Effective pixel count / Total pixel count = Coverage rate
        coverage_ratio = valid_pixels_num.divide(total_pixels_num)
        coverage_ratio = coverage_ratio.getInfo()
        print(f'>>> 第 {img_idx + 1} 景影像，有效值覆盖率: {coverage_ratio:.4f}')

        # 如果覆盖度超过设定阈值，就下载 // Download the image if the coverage exceeds the set threshold
        if coverage_ratio >= coverage_ratio_threshold:
            timestamp = selected_img.get('system:time_start').getInfo()
            date_time_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f"索引 {img_idx} 成像时间 {date_time_str}，timestamp(ms)={timestamp}")

            # 计算 TOA // Calculate TOA
            selected_img = selected_img.divide(10000)

            # 重采样 // ReSample
            # GEE下载的S2影像默认分辨率为 0.00008983 // The default resolution of the S2 images downloaded from GEE is 0.00008983
            # [x_scale (经度分辨率), x_shear, x_translate (左上角经度), y_shear, y_scale (纬度分辨率, 必须是负值), y_translate (左上角纬度)]
            # [x_scale (Lon resolution), x_shear, x_translate (Top-left lon), y_shear, y_scale (Lat resolution, must be a negative value), y_translate (Top-left lat)]
            crsTransform = (resample_resolution, 0, lon_min, 0, -resample_resolution, lat_max)

            # 设置下载路径与相关参数，并执行下载 // Set the download path and related parameters, and start downloading
            download_path = download_folderpath + '\\' + 'Sentinel2' + '_' + f'{lon_min:.2f}E_' + f'{lat_max:.2f}N_' + date_time_str.replace(' ', '_').replace(':', '-')   + '.tif'
            geemap.download_ee_image(
                image=selected_img,                 # 选择的影像数据 // Selected image data
                filename=download_path,             # 保存路径 // Download savepath
                region=rect_polygon,                # 自定义的矩形范围 // Customized rectangular range
                crs="EPSG:4326",                    # 坐标系的EPSG编号 // The EPSG code of the coordinate system
                crs_transform=crsTransform,         # 仿射参数 // Affine parameters
                resampling='bilinear'               # 重采样方式 // Resampling method
            )

            # 对下载的影像进行后处理 // Process the downloaded images
            if is_postprocess:
                Process_Downloaded_Imgs(crsTransform, download_path)

        # 如果覆盖度不满足设定阈值，则跳过该景影像
        else:
            continue
            

if __name__ == '__main__':

    # 授权与初始化GEE账户 // Authorization and initialization of GEE account
    # 账号在此电脑首次运行的话，会在浏览器中弹出授权截面，按流程操作即可
    # If this account is used for the first time on this computer, an authorization screen will pop up in the browser. Just follow the procedures to complete the process
    # 授权成功后会在 C:\Users\用户名\.config\earthengine 目录下生成一个 credentials 凭证文件
    # After the authorization is successful, a credentials file will be generated in the directory C:\Users\username\.config\earthengine
    ee.Authenticate()
    ee.Initialize(project='Your GEE Account')

    download_folderpath = r'F:\Working_Space\FY_PreProcessing\Sentinel2_toa_Download_Test'

    Sentinel2_TOA_Download(lon_min=116.48, 
                           lon_max=116.98, 
                           lat_min=30.72, 
                           lat_max=31.22, 
                           start_date_str='2025-08-01',
                           end_date_str='2025-08-07',
                           download_folderpath=download_folderpath
                           bands=['B2', 'B3', 'B4', 'B8'],
                           coverage_ratio_threshold=0.99,
                           resample_resolution=0.00008983,
                           is_postprocess=True)


